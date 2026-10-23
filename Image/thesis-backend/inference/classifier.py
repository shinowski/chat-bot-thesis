import os
import base64
import io
import json
import hashlib

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
from PIL import Image, ImageOps

from inference.gradcam import GradCAM, create_gradcam_overlay, stitch_cams
from inference.skin_detector import get_skin_crops_with_boxes

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "models",
    "resnet50_skin_finale_oe.pth"
)

OOD_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "models",
    "ood_config.json"
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

CONFIDENCE_THRESHOLD = 0.55

OOD_ENABLED = True

# Skin cropping: classify up to N_CROPS mostly-skin windows and average
# their logits. Falls back to the full image if no skin window is found.
CROP_TO_SKIN = True
N_CROPS = 5

# TEMPORARY: saves debug_crop_0.jpg ... debug_crop_N.jpg on each upload.
DEBUG_SAVE_CROPS = False

# ------------------------------------------------------------
# NORMAL-SKIN SAFETY GATE
# ------------------------------------------------------------
# A false "No Condition Detected" is the worst failure for a screening
# tool, so "normal_skin" is held to a stricter standard than the disease
# classes. If either check fails, the result becomes "inconclusive".
#
# NORMAL_MIN_CONFIDENCE: normal_skin must win by at least this probability.
# NORMAL_CROP_VETO_PROB: if ANY single crop gives a disease class at least
#   this probability, "normal" is blocked, even if the averaged logits
#   favored normal (averaging can dilute a lesion seen in only one crop).
#
# Calibrate both on the validation set (see notes) instead of trusting
# these defaults.
NORMAL_CLASS = "normal_skin"
NORMAL_GATE_ENABLED = True
NORMAL_MIN_CONFIDENCE = 0.80
NORMAL_CROP_VETO_PROB = 0.50


# ============================================================
# LOAD MODEL
# ============================================================

_checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False
)

_model = models.resnet50(weights=None)

_model.fc = nn.Linear(
    _model.fc.in_features,
    _checkpoint["num_classes"]
)

_model.load_state_dict(
    _checkpoint["model_state_dict"]
)

_model = _model.to(DEVICE)

_model.eval()


# ============================================================
# LOAD OOD CONFIG (method + threshold, calibrated in notebook)
# ============================================================

with open(OOD_CONFIG_PATH, "r") as f:
    _ood_config = json.load(f)

OOD_METHOD = _ood_config["method"]          # "energy" | "msp" | "entropy"
OOD_THRESHOLD = _ood_config["threshold"]
OOD_TEMPERATURE = _ood_config.get("temperature", 1.0)


def _ood_score(logits: torch.Tensor) -> float:
    """
    Computes the OOD score using whichever method is set in ood_config.json.

    Convention matches the notebook: HIGHER score = more OOD-like, for all
    three methods.
    """
    if OOD_METHOD == "energy":
        score = -OOD_TEMPERATURE * torch.logsumexp(logits / OOD_TEMPERATURE, dim=1)
    else:
        probs = F.softmax(logits, dim=1)
        if OOD_METHOD == "msp":
            score = -probs.max(dim=1).values
        elif OOD_METHOD == "entropy":
            score = -(probs * torch.log(probs + 1e-12)).sum(dim=1)
        else:
            raise ValueError(f"Unknown OOD method in ood_config.json: {OOD_METHOD}")

    return score.item()


# ============================================================
# CLASS MAPPING
# ============================================================

_idx_to_class = {
    v: k
    for k, v in _checkpoint["class_to_idx"].items()
}

_normal_idx = _checkpoint["class_to_idx"].get(NORMAL_CLASS)

_disease_idxs = [
    i for i in _idx_to_class
    if i != _normal_idx
]


# ============================================================
# TRANSFORM
# ============================================================

_inference_transform = transforms.Compose([
    transforms.Resize((224, 224)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# Heatmap-only transform: a larger input gives layer4 a finer map
# (448 -> 14x14 instead of 7x7), so scattered lesions can show up as
# separate hot spots. The PREDICTION still uses the 224 transform above.
CAM_INPUT_SIZE = 448

_cam_transform = transforms.Compose([
    transforms.Resize((CAM_INPUT_SIZE, CAM_INPUT_SIZE)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# GRAD-CAM
# ============================================================

# layer4 = coarse 7x7 map but class-specific (sits on the lesion).
# layer3 = finer 14x14 map but picks up edges/texture more.
# Grad-CAM++ (CAM_PLUSPLUS=True) handles multiple lesions better.
# Compare combinations on a few images and keep the best one.
CAM_LAYER = "layer4"   # "layer3" or "layer4"
CAM_PLUSPLUS = True

_cam_layer = getattr(_model, CAM_LAYER)[-1]

_gradcam = GradCAM(
    model=_model,
    target_layer=_cam_layer,
    plusplus=CAM_PLUSPLUS
)


# ============================================================
# STARTUP MESSAGE
# ============================================================

with open(MODEL_PATH, 'rb') as checkpoint_file:
    checkpoint_hasher = hashlib.sha256()
    for checkpoint_chunk in iter(lambda: checkpoint_file.read(1024 * 1024), b''):
        checkpoint_hasher.update(checkpoint_chunk)
    checkpoint_digest = checkpoint_hasher.hexdigest()

# Reports the weights and pipeline actually loaded by this process, so a
# running older service cannot be mistaken for the newly downloaded model.
MODEL_INFO = {
    'checkpoint': os.path.basename(MODEL_PATH),
    'sha256': checkpoint_digest,
    'classes': [_idx_to_class[index] for index in sorted(_idx_to_class)],
    'confidence_threshold': CONFIDENCE_THRESHOLD,
    'ood_method': OOD_METHOD,
    'ood_threshold': OOD_THRESHOLD,
    'skin_crops': N_CROPS if CROP_TO_SKIN else 0,
    'normal_gate_enabled': NORMAL_GATE_ENABLED,
    'normal_min_confidence': NORMAL_MIN_CONFIDENCE,
    'normal_crop_veto_probability': NORMAL_CROP_VETO_PROB,
    'heatmap': 'Grad-CAM++' if CAM_PLUSPLUS else 'Grad-CAM',
}

print(
    f"[classifier] Loaded ResNet50 on {DEVICE}. "
    f"Test accuracy at save time: "
    f"{_checkpoint.get('test_accuracy', 'unknown')}. "
    f"OOD gate: method={OOD_METHOD} threshold={OOD_THRESHOLD:.4f} "
    f"enabled={OOD_ENABLED}. "
    f"Normal gate: enabled={NORMAL_GATE_ENABLED} "
    f"min_conf={NORMAL_MIN_CONFIDENCE} crop_veto={NORMAL_CROP_VETO_PROB}. "
    f"Skin crops: {N_CROPS if CROP_TO_SKIN else 'off'}"
)


# ============================================================
# CONVERT GRAD-CAM TO BASE64
# ============================================================

def _gradcam_to_base64(overlay):

    # Convert RGB NumPy array to PIL
    overlay_image = Image.fromarray(
        overlay
    )

    # Save to memory instead of disk
    buffer = io.BytesIO()

    overlay_image.save(
        buffer,
        format="PNG"
    )

    # Encode PNG as Base64
    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return encoded


# ============================================================
# PREDICTION
# ============================================================

def predict(image: Image.Image) -> dict:

    """
    Crop the upload into several mostly-skin windows, average the model's
    logits across them, run the OOD gate on the averaged logits, apply the
    normal-skin safety gate, then return the classification + Grad-CAM
    (computed on every crop and stitched back onto the full image).

    Possible "status" values:
        "classified"    -> in-scope, confident result (has gradcam)
        "outside_scope" -> rejected by the OOD gate
        "inconclusive"  -> model said normal_skin but failed the stricter
                           normal-skin safety gate

    Non-"classified" results have predicted_class / confidence /
    all_probabilities / gradcam set to None and include a "message".
    """

    # --------------------------------------------------------
    # LOAD + MULTI-CROP TO SKIN
    # --------------------------------------------------------

    image = ImageOps.exif_transpose(image).convert("RGB")

    w, h = image.size

    crops, boxes = [image], [(0, 0, w, h)]

    if CROP_TO_SKIN:
        crops, boxes = get_skin_crops_with_boxes(image, N_CROPS)

    if DEBUG_SAVE_CROPS:
        for i, crop in enumerate(crops):
            crop.save(f"debug_crop_{i}.jpg")

    # --------------------------------------------------------
    # FORWARD PASS ON ALL CROPS, AVERAGE THE LOGITS
    # --------------------------------------------------------

    # IMPORTANT:
    # Do NOT use torch.no_grad() here because
    # Grad-CAM requires gradients (only matters if we proceed to classify).

    batch = torch.stack(
        [_inference_transform(crop) for crop in crops]
    ).to(DEVICE)

    all_logits = _model(
        batch
    )                                                 # (N, num_classes)

    outputs = all_logits.mean(
        dim=0,
        keepdim=True
    )                                                 # (1, num_classes)

    ood_score = _ood_score(outputs)

    # --------------------------------------------------------
    # OOD GATE — reject before running Grad-CAM if outside scope
    # --------------------------------------------------------

    if OOD_ENABLED and ood_score > OOD_THRESHOLD:
        return {
            "status": "outside_scope",
            "predicted_class": None,
            "confidence": None,
            "is_confident": False,
            "all_probabilities": None,
            "gradcam": None,
            "message": (
                "This image does not appear to match any of the 5 supported "
                "conditions (Psoriasis, Lichen Planus, Rosacea, Atopic "
                "Dermatitis, Contact Dermatitis) or normal skin. Please "
                "consult a dermatologist for further evaluation."
            ),
            "ood_score": round(ood_score, 4),
            "ood_threshold": round(OOD_THRESHOLD, 4),
        }

    # --------------------------------------------------------
    # NORMAL PREDICTION (from the averaged logits)
    # --------------------------------------------------------

    probabilities = torch.softmax(
        outputs,
        dim=1
    )[0]

    confidence, predicted_idx = torch.max(
        probabilities,
        0
    )

    predicted_idx = predicted_idx.item()

    predicted_class = _idx_to_class[
        predicted_idx
    ]

    confidence_value = round(
        confidence.item(),
        4
    )

    # --------------------------------------------------------
    # ALL CLASS PROBABILITIES
    # --------------------------------------------------------

    all_probabilities = {
        _idx_to_class[i]: round(
            p.item(),
            4
        )
        for i, p in enumerate(probabilities)
    }

    per_crop_probs_all = torch.softmax(
        all_logits,
        dim=1
    )                                                 # (N, num_classes)

    # Highest disease-class probability seen in ANY single crop
    crop_disease_max = 0.0
    if _disease_idxs:
        crop_disease_max = per_crop_probs_all[:, _disease_idxs].max().item()

    print(
        f"[predict] crops={len(crops)} {all_probabilities} "
        f"crop_disease_max={crop_disease_max:.4f}"
    )   # TEMPORARY

    # --------------------------------------------------------
    # NORMAL-SKIN SAFETY GATE
    # --------------------------------------------------------
    # "No condition detected" reads like a clearance, so it must clear a
    # higher bar than a disease prediction. Fail -> inconclusive.

    if NORMAL_GATE_ENABLED and predicted_class == NORMAL_CLASS:

        low_confidence = confidence_value < NORMAL_MIN_CONFIDENCE
        crop_veto = crop_disease_max >= NORMAL_CROP_VETO_PROB

        if low_confidence or crop_veto:
            return {
                "status": "inconclusive",
                "predicted_class": None,
                "confidence": None,
                "is_confident": False,
                "all_probabilities": None,
                "gradcam": None,
                "message": (
                    "We couldn't tell what this photo shows. It did not clearly match "
                    "normal skin or any of the five supported conditions. This is not "
                    "a clearance. Please consult a dermatologist if you are concerned."
                ),
                "inconclusive_reasons": {
                    "normal_confidence_too_low": low_confidence,
                    "disease_pattern_in_a_crop": crop_veto,
                },
                "normal_probability": confidence_value,
                "crop_disease_max": round(crop_disease_max, 4),
                "ood_score": round(ood_score, 4),
                "ood_threshold": round(OOD_THRESHOLD, 4),
            }

    # --------------------------------------------------------
    # GRAD-CAM on EVERY crop, stitched onto the full image
    # --------------------------------------------------------

    # High-res copies of the same crops, used only for the heatmap
    cam_batch = torch.stack(
        [_cam_transform(crop) for crop in crops]
    ).to(DEVICE)

    cams = [
        _gradcam.generate(
            cam_batch[i:i + 1],
            class_idx=predicted_idx,
            normalize=False
        )
        for i in range(len(crops))
    ]

    all_boxes = list(boxes)

    # Also run CAM on the whole image so lesions the skin mask missed
    # (pale / scaly areas) are still covered.
    if len(crops) > 1 or boxes[0] != (0, 0, w, h):
        full_tensor = _cam_transform(image).unsqueeze(0).to(DEVICE)

        cams.append(
            _gradcam.generate(
                full_tensor,
                class_idx=predicted_idx,
                normalize=False
            )
        )

        all_boxes.append((0, 0, w, h))

    cam_full, covered = stitch_cams(
        cams,
        all_boxes,
        image.size
    )

    overlay = create_gradcam_overlay(
        image,
        cam_full,
        covered
    )

    gradcam_base64 = _gradcam_to_base64(
        overlay
    )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {
        "status": "classified",

        "predicted_class": predicted_class,

        "confidence": confidence_value,

        "is_confident": (
            confidence_value >= CONFIDENCE_THRESHOLD
        ),

        "all_probabilities": all_probabilities,

        "gradcam": (
            "data:image/png;base64,"
            + gradcam_base64
        ),

        "ood_score": round(ood_score, 4),

        "ood_threshold": round(OOD_THRESHOLD, 4),
    }
