"""
PPT Agent 配置管理模块 - 基于参考 PPT 提取的真实风格
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any

SKILL_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = SKILL_DIR.parent.parent


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError as exc:
        logging.getLogger("aut_sci_ppt").warning("failed to load local env from %s: %s", path, exc)
    return values


LOCAL_ENV: Dict[str, str] = {}
for _env_path in (ROOT_DIR / ".env", SKILL_DIR / ".env"):
    LOCAL_ENV.update(_load_env_file(_env_path))


def get_config_value(name: str, default: str = "") -> str:
    return LOCAL_ENV.get(name) or os.environ.get(name, default)

def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("aut_sci_ppt")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class Config:
    """配置管理 - 对标参考 PPT 风格"""

    # 页面尺寸（参考PPT实测：13.33 x 7.5 英寸，宽屏16:9）
    DEFAULT_PAGE_SIZE = {"width": 13.33, "height": 7.5}
    DEFAULT_MARGINS  = {"top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5}

    # 字体规范（从参考 PPT 提取）
    DEFAULT_FONTS = {
        # 封面主标题：48pt 加粗
        "cover_title":   {"name": "微软雅黑", "size": 48, "bold": True},
        # 封面信息：20pt 加粗 楷体
        "cover_info":    {"name": "楷体",     "size": 20, "bold": True},
        # 目录/章节大字：48pt 加粗
        "section_title": {"name": "微软雅黑", "size": 48, "bold": True},
        # Part N 标记：24pt 加粗
        "part_num":      {"name": "微软雅黑", "size": 24, "bold": True},
        # 页眉章节编号：28pt 加粗
        "page_header":   {"name": "微软雅黑", "size": 28, "bold": True},
        # 内容姓名大字：36pt 加粗
        "name_large":    {"name": "微软雅黑", "size": 36, "bold": True},
        # 内容关键信息（红色高亮）：16pt 加粗
        "highlight":     {"name": "Times New Roman", "size": 16, "bold": True},
        # 正文列表项：16pt
        "body":          {"name": "Times New Roman", "size": 16, "bold": False},
        # 列表项加粗（重点词）：16pt 加粗
        "body_bold":     {"name": "Times New Roman", "size": 16, "bold": True},
        # 目录副标题英文：24pt 加粗
        "toc_sub":       {"name": "Times New Roman", "size": 24, "bold": True},
        # 结尾大字：28pt 加粗
        "ending":        {"name": "微软雅黑", "size": 28, "bold": True},
    }

    # 颜色规范（从参考 PPT 提取）
    DEFAULT_COLORS = {
        "primary":        "1E3A5F",   # 深蓝色（主色，标题栏背景）
        "secondary":      "4A90D9",   # 浅蓝色（辅助色）
        "accent_red":     "BF0000",   # 深红色（关键信息高亮，如时间/学校/成绩）
        "accent_gold":    "E8B339",   # 金色（装饰用）
        "text_black":     "000000",   # 正黑（正文主色）
        "text_dark":      "333333",   # 深灰（普通正文）
        "text_light":     "666666",   # 浅灰（次要信息）
        "background":     "FFFFFF",   # 白色背景
        "title_bar_bg":   "1E3A5F",   # 标题栏背景（深蓝）
        "title_bar_text": "FFFFFF",   # 标题栏文字（白色）
    }

    # 布局规范（从参考 PPT 提取）
    LAYOUT = {
        # 页眉条：顶部章节标记
        "header_bar": {"top": 0.0, "height": 0.7, "left": 0.0, "width": 13.33},
        # 内容区域
        "content_area": {"top": 0.9, "left": 0.5, "width": 12.3, "height": 6.1},
        # 封面标题区
        "cover_title":  {"top": 2.77, "left": 2.19, "width": 8.95, "height": 1.0},
        # 封面信息区
        "cover_info":   {"top": 4.54, "left": 4.84, "width": 7.0,  "height": 2.0},
        # 章节页 Part 编号
        "section_part": {"top": 2.57, "left": 5.5,  "width": 3.0,  "height": 0.6},
        # 章节页大标题
        "section_main": {"top": 3.30, "left": 4.5,  "width": 5.0,  "height": 1.0},
    }

    # 列表项图标（参考 PPT 使用 ➢）
    LIST_BULLET = "➢"

    CONTENT_CONFIG = {
        "cover":               {"required_fields": ["title", "author"]},
        "toc":                 {"required_fields": ["title", "items"]},
        "section":             {"required_fields": ["part_num", "part_title"]},
        "content-list":        {"required_fields": ["title", "items"], "max_items_per_page": 6},
        "content-detail":      {"required_fields": ["title", "points"]},
        "content-detail-image":{"required_fields": ["title", "points"]},
        "timeline":            {"required_fields": ["title", "events"]},
        "ending":              {"required_fields": ["message", "author"]},
    }

    def __init__(self, config_path: str = None, log_level: str = "INFO"):
        self.page_size = self.DEFAULT_PAGE_SIZE.copy()
        self.margins   = self.DEFAULT_MARGINS.copy()
        self.fonts     = self.DEFAULT_FONTS.copy()
        self.colors    = self.DEFAULT_COLORS.copy()
        self.layout    = self.LAYOUT.copy()
        self.log_level = log_level
        self.logger    = setup_logging(log_level)

    def debug(self, msg): self.logger.debug(msg)
    def info(self,  msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)


default_config = Config()
