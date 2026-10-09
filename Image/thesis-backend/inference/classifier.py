import os
import base64
import io
import json

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
from PIL import Image

from inference.gradcam import GradCAM, create_gradcam_overlay


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "models",
    "resnet50_skin_disease_classification_v10-1_oe.pth"
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
    Computes the OOD score using whichever method is set in ood_config.json,
    so changing SCORE_METHOD in the notebook and re-saving the config Just
    Works here without touching this file again.

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


# ============================================================
# GRAD-CAM
# ============================================================

# For ResNet50, layer4[-1] is the final convolutional block.
_gradcam = GradCAM(
    model=_model,
    target_layer=_model.layer4[-1]
)


# ============================================================
# STARTUP MESSAGE
# ============================================================

print(
    f"[classifier] Loaded ResNet50 on {DEVICE}. "
    f"Test accuracy at save time: "
    f"{_checkpoint.get('test_accuracy', 'unknown')}. "
    f"OOD gate: method={OOD_METHOD} threshold={OOD_THRESHOLD:.4f}"
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
    Run the OOD gate first, then the classifier + Grad-CAM only if the
    image is judged in-distribution.

    Returns (when in-scope):
        {
            "status": "classified",
            "predicted_class": str,
            "confidence": float,
            "is_confident": bool,
            "all_probabilities": {...},
            "gradcam": "data:image/png;base64,...",
            "ood_score": float,
            "ood_threshold": float
        }

    Returns (when rejected as out-of-scope):
        {
            "status": "outside_scope",
            "predicted_class": None,
            "confidence": None,
            "is_confident": False,
            "all_probabilities": None,
            "gradcam": None,
            "message": "...",
            "ood_score": float,
            "ood_threshold": float
        }
    """

    image = image.convert("RGB")

    # --------------------------------------------------------
    # PREPROCESS IMAGE
    # --------------------------------------------------------

    input_tensor = _inference_transform(
        image
    ).unsqueeze(0).to(DEVICE)


    # --------------------------------------------------------
    # FORWARD PASS
    # --------------------------------------------------------

    # IMPORTANT:
    # Do NOT use torch.no_grad() here because
    # Grad-CAM requires gradients (only matters if we proceed to classify).

    outputs = _model(
        input_tensor
    )

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
                "This image does not appear to match any of the 6 supported "
                "conditions (Psoriasis, Lichen Planus, Rosacea, Atopic "
                "Dermatitis, Contact Dermatitis, Normal Skin). Please "
                "consult a dermatologist for further evaluation."
            ),
            "ood_score": round(ood_score, 4),
            "ood_threshold": round(OOD_THRESHOLD, 4),
        }

    # --------------------------------------------------------
    # NORMAL PREDICTION
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


    # --------------------------------------------------------
    # GRAD-CAM
    # --------------------------------------------------------

    cam = _gradcam.generate(
        input_tensor,
        class_idx=predicted_idx
    )

    overlay = create_gradcam_overlay(
        image,
        cam
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