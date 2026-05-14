# PPT Agent
from .agent import PPTAgent, create_ppt
from .paper_workflow import auto_generate_ppt
from .config import Config, default_config
from .models import ParsedData, Page
from .parser.text_parser import TextParser, parse_user_input
from .paginator.smart_paginator import SmartPaginator, smart_paginate
from .generator.pptx_generator import PPTXGenerator, generate_ppt
from .enhanced_agent import EnhancedPPTAgent, create_enhanced_ppt, create_enhanced_ppt_from_pdf

__all__ = [
    'auto_generate_ppt',
    'PPTAgent',
    'create_ppt',
    'Config',
    'default_config',
    'ParsedData',
    'Page',
    'TextParser',
    'parse_user_input',
    'SmartPaginator',
    'smart_paginate',
    'PPTXGenerator',
    'generate_ppt',
    'EnhancedPPTAgent',
    'create_enhanced_ppt',
    'create_enhanced_ppt_from_pdf',
]
