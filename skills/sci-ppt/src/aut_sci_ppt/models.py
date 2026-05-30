"""
PPT Agent 数据模型 - 完整版（含图表支持）
"""
from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class CoverData:
    title: str = ""
    subtitle: str = ""
    author: str = ""
    advisor: str = ""
    direction: str = ""
    date: str = ""


@dataclass
class TOCItem:
    num: str = ""
    title: str = ""
    subtitle: str = ""


@dataclass
class TOCData:
    title: str = "目录"
    items: List[TOCItem] = field(default_factory=list)


@dataclass
class SectionData:
    part_num: str = ""
    part_title: str = ""


@dataclass
class ListItem:
    icon: str = "●"
    text: str = ""


@dataclass
class HeaderInfo:
    time: str = ""
    org: str = ""
    major: str = ""


@dataclass
class FooterInfo:
    ethnicity: str = ""
    politics: str = ""
    phone: str = ""
    email: str = ""
    hometown: str = ""


@dataclass
class ContactInfo:
    phone: str = ""
    email: str = ""


@dataclass
class FigurePlaceholder:
    """图表占位符 - 从 markdown 解析"""
    label: str = ""           # "图1" / "表2"
    caption: str = ""         # 标题文字
    fig_type: str = "figure"  # figure / table
    path: str = ""            # 图片文件路径（若已有）
    position: str = "right"   # left / right / bottom / full
    width_ratio: float = 0.45


@dataclass
class ContentListData:
    title: str = ""
    subtitle: str = ""
    part_num: str = ""
    header_info: Optional[HeaderInfo] = None
    items: List[ListItem] = field(default_factory=list)
    footer: Optional[FooterInfo] = None
    figures: List[FigurePlaceholder] = field(default_factory=list)


@dataclass
class ContentDetailData:
    title: str = ""
    subtitle: str = ""
    part_num: str = ""
    background: str = ""
    points: List[str] = field(default_factory=list)
    results: List[str] = field(default_factory=list)
    figures: List[FigurePlaceholder] = field(default_factory=list)


@dataclass
class ContentWithFigureData:
    """带图表的内容页：支持 1~4 张图多图布局"""
    title: str = ""
    subtitle: str = ""
    part_num: str = ""
    points: List[str] = field(default_factory=list)
    figure: Optional[FigurePlaceholder] = None          # 主图（兼容旧代码）
    figures: List[FigurePlaceholder] = field(default_factory=list)  # 多图列表
    layout: str = "auto"
    current_section: str = ""


@dataclass
class TimelineEvent:
    date: str = ""
    title: str = ""
    description: str = ""


@dataclass
class TimelineData:
    title: str = ""
    part_num: str = ""
    events: List[TimelineEvent] = field(default_factory=list)
    figures: List["FigurePlaceholder"] = field(default_factory=list)  # 支持图片注入


@dataclass
class EndingData:
    message: str = "感谢聆听，请批评指正！"
    author: str = ""
    advisor: str = ""
    direction: str = ""
    date: str = ""


@dataclass
class Page:
    page_type: str = ""
    data: Any = None


@dataclass
class ParsedData:
    meta: CoverData = field(default_factory=CoverData)
    sections: List[Page] = field(default_factory=list)
    toc_items: List[TOCItem] = field(default_factory=list)


# 页面类型常量
PAGE_TYPE_COVER             = "cover"
PAGE_TYPE_TOC               = "toc"
PAGE_TYPE_SECTION           = "section"
PAGE_TYPE_CONTENT_LIST      = "content-list"
PAGE_TYPE_CONTENT_DETAIL    = "content-detail"
PAGE_TYPE_CONTENT_WITH_FIG  = "content-figure"
PAGE_TYPE_TIMELINE          = "timeline"
PAGE_TYPE_ENDING            = "ending"
