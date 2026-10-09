import torch
import numpy as np
import cv2


class GradCAM:

    def __init__(self, model, target_layer):

        self.model = model
        self.target_layer = target_layer

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

    def generate(self, image_tensor, class_idx):

        self.model.eval()

        # Forward pass
        output = self.model(image_tensor)

        # Clear previous gradients
        self.model.zero_grad()

        # Score for target class
        target = output[:, class_idx]

        # Backward pass
        target.backward()

        # Get saved activations and gradients
        activations = self.activations
        gradients = self.gradients

        # Global average pooling
        weights = gradients.mean(
            dim=(2, 3),
            keepdim=True
        )

        # Weighted activation maps
        cam = (
            weights * activations
        ).sum(
            dim=1,
            keepdim=True
        )

        # ReLU
        cam = torch.relu(cam)

        # Remove dimensions
        cam = cam.squeeze().cpu().numpy()

        # Normalize
        cam -= cam.min()

        if cam.max() != 0:
            cam /= cam.max()

        return cam

    def remove_hooks(self):

        self.forward_hook.remove()
        self.backward_hook.remove()


def create_gradcam_overlay(image, cam):

    # Convert PIL image to RGB NumPy array
    original = np.array(
        image.convert("RGB")
    )

    height, width = original.shape[:2]

    # Resize CAM to original image dimensions
    cam = cv2.resize(
        cam,
        (width, height)
    )

    # Convert CAM to 0-255
    heatmap = np.uint8(
        255 * cam
    )

    # Apply heatmap
    heatmap = cv2.applyColorMap(
        heatmap,
        cv2.COLORMAP_JET
    )

    # OpenCV uses BGR
    heatmap = cv2.cvtColor(
        heatmap,
        cv2.COLOR_BGR2RGB
    )

    # Overlay heatmap on original
    overlay = cv2.addWeighted(
        original,
        0.55,
        heatmap,
        0.45,
        0
    )

    return overlay