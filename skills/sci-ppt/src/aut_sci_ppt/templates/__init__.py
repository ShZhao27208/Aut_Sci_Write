"""
PPT Agent 模板系统
"""
from .base import BaseTemplate
from .cover import CoverTemplate
from .toc import TOCTemplate
from .section import SectionTemplate
from .content_list import ContentListTemplate
from .content_detail import ContentDetailTemplate
from .timeline import TimelineTemplate
from .ending import EndingTemplate

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
