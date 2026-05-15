#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Image Processor Module

Responsibilities:
- Save figure/sub-figure images to disk as PNG/JPG
- Generate output filenames (figure_2.png, figure_2c.png)
- Report file size and dimensions
"""

import os
import numpy as np
from PIL import Image
from .utils import get_logger
from .exceptions import OutputError

logger = get_logger()


class ImageProcessor:
    """Handle image format conversion and file output."""

    def __init__(self, output_dir: str = ".", fmt: str = "png"):
        self.output_dir = output_dir
        self.fmt = fmt.lower()
        os.makedirs(self.output_dir, exist_ok=True)

    def save_figure(self, image: np.ndarray, figure_num: int) -> str:
        """
        Save a figure image to disk.
        
        Args:
            image: numpy array (RGB) of the figure
            figure_num: figure number
        
        Returns:
            str: output file path
        
        Raises:
            ValueError: if image is None or empty
            OutputError: if saving fails
        """
        self._validate_image(image, f"Figure {figure_num}")
        filename = self._generate_filename(figure_num)
        return self._save(image, filename)

    def save_subfigure(self, image: np.ndarray, figure_num: int, sublabel: str) -> str:
        """
        Save a sub-figure image to disk.
        
        Args:
            image: numpy array (RGB) of the sub-figure
            figure_num: figure number
            sublabel: sub-figure label (e.g., "c")
        
        Returns:
            str: output file path (e.g., figure_2c.png)
        
        Raises:
            ValueError: if image is None or empty
            OutputError: if saving fails
        """
        self._validate_image(image, f"Figure {figure_num}{sublabel}")
        filename = self._generate_filename(figure_num, sublabel)
        return self._save(image, filename)

    def _save(self, image: np.ndarray, filename: str) -> str:
        """Save numpy array as image file, wrapping failures in OutputError."""
        filepath = os.path.join(self.output_dir, filename)
        try:
            img = Image.fromarray(image)
            if self.fmt in ("jpg", "jpeg"):
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                img.save(filepath, quality=95)
            else:
                img.save(filepath)
        except Exception as e:
            raise OutputError(filepath, str(e)) from e

        size_kb = os.path.getsize(filepath) / 1024
        w, h = img.size
        logger.info(f"Saved: {filename} ({w}x{h}, {size_kb:.0f} KB)")
        return filepath

    def _generate_filename(self, figure_num: int, sublabel: str = None) -> str:
        """Generate output filename following naming convention."""
        if sublabel:
            return f"figure_{figure_num}{sublabel.lower()}.{self.fmt}"
        return f"figure_{figure_num}.{self.fmt}"

    def _validate_image(self, image: np.ndarray, context: str = "image"):
        """Raise ValueError if image is None or has zero dimensions."""
        if image is None:
            raise ValueError(f"{context}: image is None")
        if not isinstance(image, np.ndarray):
            raise ValueError(f"{context}: expected numpy array, got {type(image).__name__}")
        if image.size == 0:
            raise ValueError(f"{context}: image has zero dimensions")

