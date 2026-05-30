"""
PDF 图片抓取器 - 智能裁切版
只截取页面中的图表区域，过滤正文文字块
"""

from __future__ import annotations

import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExtractedFigure:
    label: str
    page: int
    path: str
    caption: str = ""


class PDFFigureExtractor:
    def __init__(self, pdf_path: str, output_dir: str = "figures"):
        import fitz

        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.doc = fitz.open(pdf_path)

    # ─────────────────────────────────────────────
    #  核心：检测页面中图表区域的 bbox
    # ─────────────────────────────────────────────
    def _detect_figure_bbox(self, page) -> Optional["fitz.Rect"]:
        """
        策略：
        1. 获取页面所有图片的位置 → 合并为图片区域
        2. 获取页面所有文字块位置 → 识别正文区域
        3. 用图片区域 + 适当 padding，排除正文区域，得到纯图表区域
        """
        import fitz

        page_rect = page.rect  # 页面总矩形
        W, H = page_rect.width, page_rect.height

        # ── 1. 收集页面内所有嵌入图片的位置 ──────────────
        img_rects = []
        for img_info in page.get_image_info(xrefs=True):
            r = fitz.Rect(img_info["bbox"])
            # 过滤极小装饰图（宽或高 < 5% 页面）
            if r.width > W * 0.05 and r.height > H * 0.05:
                img_rects.append(r)

        if not img_rects:
            return None  # 本页无有效图片

        # ── 2. 合并所有图片区域为一个大 bbox ─────────────
        x0 = min(r.x0 for r in img_rects)
        y0 = min(r.y0 for r in img_rects)
        x1 = max(r.x1 for r in img_rects)
        y1 = max(r.y1 for r in img_rects)

        # ── 3. 向外扩展 padding（捕捉图注/坐标轴标签）────
        PAD = 15  # points
        x0 = max(0, x0 - PAD)
        y0 = max(0, y0 - PAD)
        x1 = min(W, x1 + PAD)
        y1 = min(H, y1 + PAD)

        # ── 4. 检测正文文字块，排除正文区域 ──────────────
        # 正文特征：大量连续文字，字号相对小，行宽接近页面宽度
        text_blocks = page.get_text("blocks")  # [(x0,y0,x1,y1,text,block_no,type)]
        body_y_ranges = []
        for blk in text_blocks:
            bx0, by0, bx1, by1, txt, *_ = blk
            if len(txt.strip()) < 20:
                continue
            blk_w = bx1 - bx0
            # 判断为正文：宽度 > 页面60%，且与图片区域有重叠
            if blk_w > W * 0.6:
                body_y_ranges.append((by0, by1))

        # 若正文区域与图片区域有垂直重叠，裁掉重叠部分
        for by0, by1 in body_y_ranges:
            overlap_y0 = max(y0, by0)
            overlap_y1 = min(y1, by1)
            if overlap_y1 > overlap_y0:  # 有重叠
                overlap_h = overlap_y1 - overlap_y0
                fig_h = y1 - y0
                if overlap_h / fig_h > 0.3:
                    # 正文在图片下方 → 裁掉下方
                    if by0 > (y0 + y1) / 2:
                        y1 = min(y1, by0 - 2)
                    # 正文在图片上方 → 裁掉上方
                    else:
                        y0 = max(y0, by1 + 2)

        if y1 <= y0 or x1 <= x0:
            return None

        return fitz.Rect(x0, y0, x1, y1)

    # ─────────────────────────────────────────────
    #  按名称+页码截取图表区域
    # ─────────────────────────────────────────────
    def extract_named_figures(
        self, fig_map: Dict[str, int], dpi: int = 180
    ) -> List[ExtractedFigure]:
        """
        fig_map: {"图1": 4, "图2": 5, ...}  (1-indexed 页码)
        只截取图表区域，不包含正文
        """
        import fitz

        figures = []
        for label, page_1idx in fig_map.items():
            page_0idx = page_1idx - 1
            if page_0idx < 0 or page_0idx >= len(self.doc):
                continue

            page = self.doc[page_0idx]
            fig_rect = self._detect_figure_bbox(page)

            filename = f"fig_{label.replace(' ', '_')}_p{page_1idx}.png"
            out_path = os.path.join(self.output_dir, filename)

            if fig_rect:
                # 截取图表区域
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                clip = fig_rect
                pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            else:
                # 无法检测到图片区域 → 降级为整页（fallback）
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)

            pix.save(out_path)
            figures.append(
                ExtractedFigure(
                    label=label, page=page_0idx, path=out_path, caption=label
                )
            )
            print(
                f"  {label}: {'图表区域截取' if fig_rect else '整页fallback'} -> {os.path.basename(out_path)}"
            )

        return figures

    # ─────────────────────────────────────────────
    #  整页渲染（备用）
    # ─────────────────────────────────────────────
    def extract_page_as_image(self, page_num: int, dpi: int = 150) -> str:
        import fitz

        page = self.doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        path = os.path.join(self.output_dir, f"page_{page_num + 1}.png")
        pix.save(path)
        return path

    def extract_figures_by_pages(
        self, page_nums: List[int], dpi: int = 150
    ) -> List[ExtractedFigure]:
        figures = []
        for pn in page_nums:
            if 0 <= pn < len(self.doc):
                path = self.extract_page_as_image(pn, dpi)
                figures.append(
                    ExtractedFigure(
                        label=f"Fig.(p{pn + 1})",
                        page=pn,
                        path=path,
                        caption=f"PDF第{pn + 1}页",
                    )
                )
        return figures

    def extract_all_figures(self, dpi: int = 150) -> List[ExtractedFigure]:
        figures = []
        fig_count = 0
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            for img_idx, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                try:
                    base_image = self.doc.extract_image(xref)
                    if (
                        base_image.get("width", 0) < 100
                        or base_image.get("height", 0) < 100
                    ):
                        continue
                    fig_count += 1
                    filename = f"fig_{page_num + 1}_{img_idx + 1}.{base_image['ext']}"
                    out_path = os.path.join(self.output_dir, filename)
                    with open(out_path, "wb") as f:
                        f.write(base_image["image"])
                    figures.append(
                        ExtractedFigure(
                            label=f"Fig.{fig_count}",
                            page=page_num,
                            path=out_path,
                            caption=f"第{page_num + 1}页图片",
                        )
                    )
                except Exception:
                    continue
        return figures


# ═══════════════════════════════════════════════
#  图片提取策略选择：使用内置 PDFFigureExtractor
# ═══════════════════════════════════════════════


def get_figure_extractor(
    pdf_path: str, output_dir: str, use_skill: bool = True, skill_script: str = None
) -> List[ExtractedFigure]:
    """
    统一图片提取入口：使用内置 PDFFigureExtractor (180 DPI)。

    Args:
        pdf_path: PDF 文件路径
        output_dir: 图片输出目录
        use_skill: 已废弃，保留以兼容旧调用签名
        skill_script: 已废弃，保留以兼容旧调用签名

    Returns:
        提取的 ExtractedFigure 列表（提取失败时返回空列表）
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        extractor = PDFFigureExtractor(pdf_path, output_dir)
        figures = extractor.extract_all_figures(dpi=180)
    except Exception as exc:
        print(f"  ⚠️  图片提取失败（{exc}），跳过图片")
        return []

    print(f"  ✅ 内置提取器完成: {len(figures)} 张图片")
    return figures

