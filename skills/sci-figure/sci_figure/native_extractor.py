"""
Native Extractor — extract embedded raster images directly from PDF structure.

Uses PyMuPDF's get_images() + get_image_bbox() to locate images that are
embedded as XObjects in the PDF. This gives pixel-perfect boundaries for
raster figures but cannot detect vector-drawn figures.
"""

from __future__ import annotations

import numpy as np
import fitz
from sci_figure.utils import get_logger

logger = get_logger()


class NativeExtractor:
    """Extract embedded raster images from PDF pages via PyMuPDF."""

    def __init__(self, fitz_doc: fitz.Document):
        self.doc = fitz_doc

    def extract_page_images(self, page_num: int) -> list[dict]:
        """
        Get all embedded images on a page with their bounding boxes.

        Returns:
            [{"bbox_pdf": (x0,y0,x1,y1), "xref": int, "size": (w,h)}, ...]
            bbox is in PDF points (72 DPI).
        """
        page = self.doc[page_num]
        images = page.get_images(full=True)

        if not images:
            return []

        results = []
        for img_info in images:
            xref = img_info[0]
            try:
                bbox = page.get_image_bbox(img_info)
                if bbox.is_empty or bbox.is_infinite:
                    continue

                img_width = img_info[2]
                img_height = img_info[3]

                results.append({
                    "bbox_pdf": (bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                    "xref": xref,
                    "size": (img_width, img_height),
                    "area_pdf": bbox.width * bbox.height,
                })
            except Exception as e:
                logger.debug(f"Skip image xref={xref}: {e}")
                continue

        logger.info(f"Page {page_num}: {len(results)} embedded image(s) found")
        return results

    def match_to_caption(
        self,
        images: list[dict],
        caption_bbox_pdf: tuple,
        page_size: tuple,
        column_bounds_pdf: tuple = None,
        exclude_xrefs: set[int] | None = None,
    ) -> dict | None:
        """
        Find the embedded image best matching a caption position.

        Args:
            images: list from extract_page_images()
            caption_bbox_pdf: (x0, y0, x1, y1) of caption in PDF points
            page_size: (width, height) in PDF points
            column_bounds_pdf: optional (x_start, x_end) column constraint
            exclude_xrefs: xrefs already claimed by other captions on this page

        Returns:
            Best matching image dict, or None.
        """
        if not images:
            return None

        cap_x0, cap_y0, cap_x1, cap_y1 = caption_bbox_pdf
        page_w, page_h = page_size
        cap_width = cap_x1 - cap_x0
        cap_center_x = (cap_x0 + cap_x1) / 2

        # Filter: only consider images with reasonable size (> 2% of page)
        min_area = page_w * page_h * 0.02
        candidates = [img for img in images if img["area_pdf"] >= min_area]

        # Exclude already-claimed images
        if exclude_xrefs:
            candidates = [img for img in candidates if img["xref"] not in exclude_xrefs]

        if not candidates:
            return None

        best = None
        best_score = -1.0

        for img in candidates:
            ix0, iy0, ix1, iy1 = img["bbox_pdf"]
            img_center_x = (ix0 + ix1) / 2

            # Column constraint
            if column_bounds_pdf:
                col_start, col_end = column_bounds_pdf
                if not (col_start <= img_center_x <= col_end):
                    continue

            # Image should be above caption
            if iy0 > cap_y0 + 5:
                continue

            # Horizontal overlap with caption
            overlap_x = max(0, min(ix1, cap_x1) - max(ix0, cap_x0))
            overlap_ratio = overlap_x / cap_width if cap_width > 0 else 0

            # Vertical proximity
            dist = cap_y0 - iy1
            if dist < 0:
                dist = 0
            proximity = max(0, 1.0 - dist / (page_h * 0.3))

            # Center alignment
            center_offset = abs(img_center_x - cap_center_x) / page_w
            alignment = max(0, 1.0 - center_offset * 2)

            score = overlap_ratio * 0.4 + proximity * 0.4 + alignment * 0.2

            if score > best_score:
                best_score = score
                best = img

        if best and best_score > 0.3:
            logger.info(
                f"Native match: xref={best['xref']} "
                f"bbox={best['bbox_pdf']} (score={best_score:.2f})"
            )
            return best

        return None

    def merge_adjacent_images(
        self, images: list[dict], gap_threshold: float = 10.0
    ) -> list[dict]:
        """
        Merge images that are adjacent (likely parts of one composite figure).

        If multiple small images are arranged in a grid with gaps < threshold,
        merge them into one bounding box.
        """
        if len(images) <= 1:
            return images

        # Sort by position (top-left)
        sorted_imgs = sorted(images, key=lambda i: (i["bbox_pdf"][1], i["bbox_pdf"][0]))

        merged = []
        current_group = [sorted_imgs[0]]

        for img in sorted_imgs[1:]:
            # Check if this image is adjacent to the current group
            group_bbox = self._group_bbox(current_group)
            if self._is_adjacent(group_bbox, img["bbox_pdf"], gap_threshold):
                current_group.append(img)
            else:
                merged.append(self._merge_group(current_group))
                current_group = [img]

        merged.append(self._merge_group(current_group))
        return merged

    def extract_image_data(self, xref: int) -> np.ndarray | None:
        """Extract actual pixel data for an embedded image by xref."""
        try:
            pix = fitz.Pixmap(self.doc, xref)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            return img
        except Exception as e:
            logger.warning(f"Cannot extract image xref={xref}: {e}")
            return None

    def _is_adjacent(self, bbox1: tuple, bbox2: tuple, threshold: float) -> bool:
        """Check if two bboxes are adjacent (within threshold gap)."""
        x0a, y0a, x1a, y1a = bbox1
        x0b, y0b, x1b, y1b = bbox2

        # Vertical adjacency
        v_gap = max(0, y0b - y1a)
        # Horizontal adjacency
        h_gap = max(0, x0b - x1a)

        # Check horizontal overlap
        h_overlap = max(0, min(x1a, x1b) - max(x0a, x0b))
        v_overlap = max(0, min(y1a, y1b) - max(y0a, y0b))

        if h_overlap > 0 and v_gap <= threshold:
            return True
        if v_overlap > 0 and h_gap <= threshold:
            return True

        return False

    def _group_bbox(self, group: list[dict]) -> tuple:
        """Get bounding box of a group of images."""
        x0 = min(img["bbox_pdf"][0] for img in group)
        y0 = min(img["bbox_pdf"][1] for img in group)
        x1 = max(img["bbox_pdf"][2] for img in group)
        y1 = max(img["bbox_pdf"][3] for img in group)
        return (x0, y0, x1, y1)

    def _merge_group(self, group: list[dict]) -> dict:
        """Merge a group of adjacent images into one entry."""
        if len(group) == 1:
            return group[0]

        bbox = self._group_bbox(group)
        total_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        return {
            "bbox_pdf": bbox,
            "xref": group[0]["xref"],  # use first image's xref
            "size": (int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])),
            "area_pdf": total_area,
            "merged_from": len(group),
        }
