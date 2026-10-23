import torch
import numpy as np
import cv2


class GradCAM:

    def __init__(self, model, target_layer, plusplus=True):

        self.model = model
        self.target_layer = target_layer
        self.plusplus = plusplus

        self.activations = None
        self.gradients = None

        self.forward_hook = target_layer.register_forward_hook(
            self.save_activation
        )

        self.backward_hook = target_layer.register_full_backward_hook(
            self.save_gradient
        )

    def save_activation(self, module, input, output):
        self.activations = output.detach()

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, image_tensor, class_idx, normalize=True):
        """
        Returns a 2D CAM (numpy). Pass normalize=False when stitching
        several crops so they can be normalized together afterwards.
        """

        self.model.eval()

        output = self.model(image_tensor)

        self.model.zero_grad()

        output[:, class_idx].backward()

        acts, grads = self.activations, self.gradients

        if self.plusplus:
            # Grad-CAM++ weighting
            g2, g3 = grads ** 2, grads ** 3
            sum_acts = acts.sum(dim=(2, 3), keepdim=True)
            alpha = g2 / (2 * g2 + sum_acts * g3 + 1e-7)
            weights = (alpha * torch.relu(grads)).sum(dim=(2, 3), keepdim=True)
        else:
            weights = grads.mean(dim=(2, 3), keepdim=True)

        cam = torch.relu((weights * acts).sum(dim=1, keepdim=True))
        cam = cam.squeeze().cpu().numpy()

        if normalize:
            cam -= cam.min()
            if cam.max() != 0:
                cam /= cam.max()

        return cam

    def remove_hooks(self):
        self.forward_hook.remove()
        self.backward_hook.remove()


def stitch_cams(cams, boxes, image_size):
    """
    Paste per-crop CAMs onto a full-image canvas (max where they overlap).
    Normalizes globally so a crop with no lesion isn't blown up to red.

    cams:       list of 2D numpy arrays (unnormalized)
    boxes:      list of (left, top, right, bottom) in original pixels
    image_size: (width, height) of the original image
    Returns (canvas, covered) where covered marks pixels any crop looked at.
    """
    w, h = image_size
    canvas = np.zeros((h, w), dtype=np.float32)
    covered = np.zeros((h, w), dtype=bool)

    for cam, (l, t, r, b) in zip(cams, boxes):
        resized = cv2.resize(cam.astype(np.float32), (r - l, b - t))
        canvas[t:b, l:r] = np.maximum(canvas[t:b, l:r], resized)
        covered[t:b, l:r] = True

    canvas -= canvas[covered].min()

    if canvas.max() > 0:
        canvas /= canvas.max()

    # Soften seams at crop borders
    k = int(max(w, h) * 0.05) | 1   # odd kernel size
    canvas = cv2.GaussianBlur(canvas, (k, k), 0)

    if canvas.max() > 0:
        canvas /= canvas.max()

    return canvas, covered


def create_gradcam_overlay(image, cam, covered=None, max_side=1024):

    original = np.array(image.convert("RGB"))
    h, w = original.shape[:2]

    # Keep the base64 PNG a sane size for big photos
    scale = min(1.0, max_side / max(h, w))

    if scale < 1.0:
        nw, nh = int(w * scale), int(h * scale)
        original = cv2.resize(original, (nw, nh))
        cam = cv2.resize(cam, (nw, nh))

        if covered is not None:
            covered = cv2.resize(
                covered.astype(np.uint8), (nw, nh)
            ).astype(bool)

        h, w = nh, nw

    cam = cv2.resize(cam, (w, h))

    heatmap = cv2.applyColorMap(
        np.uint8(255 * cam),
        cv2.COLORMAP_JET
    )

    # OpenCV uses BGR
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

    overlay = cv2.addWeighted(original, 0.55, heatmap, 0.45, 0)

    # Areas no crop looked at stay as the plain photo
    if covered is not None:
        overlay[~covered] = original[~covered]

    return overlay