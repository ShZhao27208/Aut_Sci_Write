"""Image Processor — save figures to disk with format conversion."""

from __future__ import annotations

import os
import numpy as np
from PIL import Image
from sci_figure.utils import get_logger

logger = get_logger()


class ImageProcessor:
    """Save figure images to disk."""

    def __init__(self, output_dir: str = ".", fmt: str = "png"):
        self.output_dir = output_dir
        self.fmt = fmt.lower()
        os.makedirs(self.output_dir, exist_ok=True)

    def save_figure(self, image: np.ndarray, figure_num: int) -> str:
        filename = f"figure_{figure_num}.{self.fmt}"
        return self._save(image, filename)

    def save_subfigure(self, image: np.ndarray, figure_num: int, sublabel: str) -> str:
        filename = f"figure_{figure_num}{sublabel.lower()}.{self.fmt}"
        return self._save(image, filename)

    def save_annotated(self, image: np.ndarray, name: str) -> str:
        filename = f"{name}.{self.fmt}"
        return self._save(image, filename)

    def _save(self, image: np.ndarray, filename: str) -> str:
        if image is None or image.size == 0:
            raise ValueError(f"Cannot save empty image: {filename}")

        filepath = os.path.join(self.output_dir, filename)
        img = Image.fromarray(image)

        if self.fmt in ("jpg", "jpeg"):
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(filepath, quality=95)
        else:
            img.save(filepath)

        size_kb = os.path.getsize(filepath) / 1024
        w, h = img.size
        logger.info(f"Saved: {filename} ({w}x{h}, {size_kb:.0f} KB)")
        return filepath
