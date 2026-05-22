"""
Page Annotator — multimodal verification layer.

Renders page images with detection overlays (bounding boxes, labels)
so that multimodal LLMs can visually verify and correct extraction results.
"""

from __future__ import annotations

import numpy as np
import cv2
from sci_figure.utils import get_logger

logger = get_logger()

# Color scheme (BGR for OpenCV)
COLOR_FIGURE = (0, 0, 255)      # Red — figure region
COLOR_CAPTION = (255, 100, 0)   # Blue — caption
COLOR_SUBFIG = (0, 200, 0)     # Green — subfigure splits
COLOR_LABEL = (0, 0, 200)      # Dark red — text labels


class PageAnnotator:
    """Generate annotated page images for visual verification."""

    def __init__(self, line_thickness: int = 3, font_scale: float = 0.8):
        self.line_thickness = line_thickness
        self.font_scale = font_scale

    def annotate_detections(
        self,
        page_image: np.ndarray,
        figures: list[dict],
        captions: list[dict] = None,
    ) -> np.ndarray:
        """
        Draw detection boxes on a page image.

        Args:
            page_image: RGB numpy array of rendered page
            figures: list of figure dicts with "bbox_px" and "number"
            captions: optional list of caption dicts with "bbox_pdf" converted to px

        Returns:
            Annotated RGB image (copy, original unchanged)
        """
        annotated = page_image.copy()
        # Convert RGB to BGR for OpenCV drawing
        annotated = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)

        for fig in figures:
            bbox = fig.get("bbox_px") or fig.get("bbox")
            if not bbox:
                continue
            x0, y0, x1, y1 = [int(v) for v in bbox]

            # Draw figure bounding box
            cv2.rectangle(annotated, (x0, y0), (x1, y1), COLOR_FIGURE, self.line_thickness)

            # Label
            label = f"Fig.{fig['number']}"
            engine = fig.get("engine_used", "")
            if engine:
                label += f" [{engine}]"

            self._put_label(annotated, label, x0, y0 - 10, COLOR_FIGURE)

        if captions:
            for cap in captions:
                bbox = cap.get("bbox_px")
                if not bbox:
                    continue
                x0, y0, x1, y1 = [int(v) for v in bbox]
                cv2.rectangle(annotated, (x0, y0), (x1, y1), COLOR_CAPTION, 2)

        # Convert back to RGB
        annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        return annotated

    def annotate_subfigures(
        self,
        figure_image: np.ndarray,
        subfigures: dict[str, tuple],
    ) -> np.ndarray:
        """
        Draw subfigure split boundaries on a figure image.

        Args:
            figure_image: RGB numpy array of the cropped figure
            subfigures: {"a": (x0,y0,x1,y1), "b": ...}

        Returns:
            Annotated RGB image
        """
        annotated = cv2.cvtColor(figure_image.copy(), cv2.COLOR_RGB2BGR)

        for label, bbox in subfigures.items():
            x0, y0, x1, y1 = [int(v) for v in bbox]
            cv2.rectangle(annotated, (x0, y0), (x1, y1), COLOR_SUBFIG, 2)
            self._put_label(annotated, f"({label})", x0 + 5, y0 + 20, COLOR_SUBFIG)

        return cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

    def save(self, image: np.ndarray, output_path: str):
        """Save annotated image to file."""
        from PIL import Image
        img = Image.fromarray(image)
        img.save(output_path)
        logger.info(f"Annotated image saved: {output_path}")

    def _put_label(self, img, text, x, y, color):
        """Draw text label with background."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(text, font, self.font_scale, 1)
        y = max(th + 5, y)
        cv2.rectangle(img, (x, y - th - 4), (x + tw + 4, y + 4), (255, 255, 255), -1)
        cv2.putText(img, text, (x + 2, y), font, self.font_scale, color, 2)
