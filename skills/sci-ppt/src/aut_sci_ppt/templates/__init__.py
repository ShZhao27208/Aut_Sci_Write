"""
PPT Agent 模板系统
"""
from .base import BaseTemplate
from .content_detail import ContentDetailTemplate
from .content_list import ContentListTemplate
from .cover import CoverTemplate
from .ending import EndingTemplate
from .section import SectionTemplate
from .timeline import TimelineTemplate
from .toc import TOCTemplate

__all__ = [
    "TEMPLATE_MAP",
    "BaseTemplate",
    "ContentDetailTemplate",
    "ContentListTemplate",
    "CoverTemplate",
    "EndingTemplate",
    "SectionTemplate",
    "TOCTemplate",
    "TimelineTemplate",
    "get_template",
    "list_templates",
    "register_template",
]

# 模板映射
TEMPLATE_MAP = {
    'cover': CoverTemplate,
    'toc': TOCTemplate,
    'section': SectionTemplate,
    'content-list': ContentListTemplate,
    'content-detail': ContentDetailTemplate,
    'timeline': TimelineTemplate,
    'ending': EndingTemplate,
}


def get_template(page_type: str, config=None):
    """获取模板实例
    
    Args:
        page_type: 页面类型
        config: 配置对象
    
    Returns:
        模板实例
    """
    template_class = TEMPLATE_MAP.get(page_type, CoverTemplate)
    return template_class(config)


def register_template(page_type: str, template_class):
    """注册自定义模板
    
    Args:
        page_type: 页面类型标识
        template_class: 模板类
    """
    TEMPLATE_MAP[page_type] = template_class


def list_templates():
    """列出所有可用的模板"""
    return list(TEMPLATE_MAP.keys())
