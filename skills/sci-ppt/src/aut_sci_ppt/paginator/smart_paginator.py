"""
PPT Agent 智能分页器 - 终版
单图页合并：在 parser 阶段就把同章节多张图+文字整合为一页或两页
"""

from typing import List
from ..models import (
    ParsedData,
    Page,
    TOCItem,
    TOCData,
    ContentListData,
    ContentWithFigureData,
    EndingData,
    FigurePlaceholder,
    PAGE_TYPE_COVER,
    PAGE_TYPE_TOC,
    PAGE_TYPE_SECTION,
    PAGE_TYPE_CONTENT_LIST,
    PAGE_TYPE_CONTENT_WITH_FIG,
    PAGE_TYPE_ENDING,
)
from ..config import default_config

import os


def _aspect(path):
    if not path or not os.path.isfile(path):
        return 1.5
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as im:
            w, h = im.size
            return w / h if h else 1.5
    except Exception:
        return 1.5


class SmartPaginator:
    def __init__(self, config=None):
        self.config = config or default_config
        self.page_config = self.config.CONTENT_CONFIG

    def paginate(self, parsed_data: ParsedData) -> List[Page]:
        pages = []
        pages.append(Page(page_type=PAGE_TYPE_COVER, data=parsed_data.meta))

        deduped = self._dedup(parsed_data.sections)

        section_titles = [
            p.data.part_title
            for p in deduped
            if p.page_type == PAGE_TYPE_SECTION and getattr(p.data, "part_title", "")
        ]
        if len(section_titles) > 1:
            toc = TOCData(title="目录")
            for i, t in enumerate(section_titles, 1):
                toc.items.append(TOCItem(num=str(i), title=t))
            pages.append(Page(page_type=PAGE_TYPE_TOC, data=toc))

        max_items = self.page_config.get("content-list", {}).get(
            "max_items_per_page", 7
        )

        last_section_title = ""  # 跟踪当前所属章节，用于自动注入 current_section

        for page in deduped:
            # 跟踪最近的 section 页标题
            if page.page_type == PAGE_TYPE_SECTION:
                last_section_title = getattr(page.data, "part_title", "") or ""

            figures = getattr(page.data, "figures", []) or []

            # ── 有图的内容页：智能分配 ──────────────────────
            if figures and page.page_type in (PAGE_TYPE_CONTENT_LIST, "content-detail"):
                text_items = self._extract_texts(page)
                pages.extend(
                    self._assign_fig_pages(
                        page, text_items, figures, current_section=last_section_title
                    )
                )

            elif page.page_type == PAGE_TYPE_CONTENT_LIST:
                items = getattr(page.data, "items", []) or []
                if len(items) > max_items:
                    for i in range(0, len(items), max_items):
                        chunk = ContentListData(
                            title=page.data.title,
                            subtitle=getattr(page.data, "subtitle", ""),
                            part_num=getattr(page.data, "part_num", ""),
                            header_info=getattr(page.data, "header_info", None),
                            items=items[i : i + max_items],
                        )
                        pages.append(Page(page_type=PAGE_TYPE_CONTENT_LIST, data=chunk))
                else:
                    pages.append(page)
            else:
                pages.append(page)

            # 自动注入 current_section 到所有内容页（如果数据模型支持且未手动设置）
            if last_section_title and page.page_type not in (
                PAGE_TYPE_COVER,
                PAGE_TYPE_TOC,
                PAGE_TYPE_SECTION,
                PAGE_TYPE_ENDING,
            ):
                if hasattr(page.data, "current_section"):
                    if not page.data.current_section:
                        page.data.current_section = last_section_title

        ending = EndingData(
            message="感谢聆听，请批评指正！",
            author=parsed_data.meta.author,
            advisor=parsed_data.meta.advisor,
            direction=parsed_data.meta.direction,
            date=parsed_data.meta.date,
        )
        pages.append(Page(page_type=PAGE_TYPE_ENDING, data=ending))
        return pages

    def _extract_texts(self, page) -> List[str]:
        if hasattr(page.data, "items"):
            return [
                item.text if hasattr(item, "text") else str(item)
                for item in (page.data.items or [])
            ]
        pts = list(getattr(page.data, "points", []) or [])
        res = list(getattr(page.data, "results", []) or [])
        return pts + res

    def _assign_fig_pages(
        self,
        page,
        texts: List[str],
        figures: List[FigurePlaceholder],
        current_section: str = "",
    ) -> List[Page]:
        """
        核心逻辑：把文字和图片合并到尽可能少的页面
        规则：
          - 每页最多 4 张图
          - 第一页：文字 + 图（最多4张）
          - 图超过4张：从第5张起新开页，继续带文字
        """
        title = getattr(page.data, "title", "")
        part_num = getattr(page.data, "part_num", "")
        result = []

        if not figures:
            d = ContentListData(
                title=title,
                part_num=part_num,
                items=[
                    __import__("aut_sci_ppt.models", fromlist=["ListItem"]).ListItem(
                        text=t
                    )
                    for t in texts
                ],
            )
            return [Page(page_type=PAGE_TYPE_CONTENT_LIST, data=d)]

        MAX_FIGS = 4
        # 按每页最多4张分组
        for chunk_start in range(0, len(figures), MAX_FIGS):
            chunk = figures[chunk_start : chunk_start + MAX_FIGS]
            d = ContentWithFigureData(
                title=title,
                part_num=part_num,
                points=texts,  # 每页都带文字
                figure=chunk[0],  # 主图
                figures=chunk,  # 全部图（模板负责布局）
                layout="auto",
                current_section=current_section,  # 自动绑定章节名
            )
            result.append(Page(page_type=PAGE_TYPE_CONTENT_WITH_FIG, data=d))

        return result

    def _dedup(self, sections):
        result, seen, i = [], set(), 0
        while i < len(sections):
            page = sections[i]
            if page.page_type == PAGE_TYPE_SECTION:
                key = (
                    getattr(page.data, "part_num", ""),
                    getattr(page.data, "part_title", ""),
                )
                if key in seen:
                    i += 1
                    if i < len(sections) and sections[i].page_type != PAGE_TYPE_SECTION:
                        i += 1
                    continue
                seen.add(key)
            result.append(page)
            i += 1
        return result


def smart_paginate(parsed_data):
    return SmartPaginator().paginate(parsed_data)
