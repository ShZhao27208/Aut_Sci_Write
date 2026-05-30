"""
PPT Agent 主入口
"""

from typing import Dict, List
from .config import Config, default_config
from .models import ParsedData
from .parser.text_parser import TextParser
from .paginator.smart_paginator import SmartPaginator
from .generator.pptx_generator import PPTXGenerator


class PPTAgent:
    """
    PPT生成Agent

    用法示例：

    ```python
    from aut_sci_ppt import PPTAgent

    agent = PPTAgent()

    # 方式1: 使用文本输入
    user_input = '''
    主题：研究生推免申请汇报
    申请人：赵烁
    导师：武海军教授
    申请方向：高性能新型智能材料
    时间：2025-9-15

    1. 教育背景
    - 2022.09-2026.07 重庆交通大学 材料科学与工程专业
    - 绩点：3.61/4.0

    2. 获奖经历
    - "徕卡杯"第十三届全国大学生金相技能大赛 国三 2024年
    - 第六届重庆市大学生物理创新竞赛 市一 2023年
    '''

    output_path = agent.generate(user_input, "output.pptx")
    print(f"PPT已生成: {output_path}")
    ```
    """

    def __init__(self, config: Config = None, scene: str = "推免"):
        """
        初始化Agent

        Args:
            config: 配置对象，默认使用全局配置
            scene: 场景类型，"推免" 或 "文献汇报"。
                   "文献汇报" 会启用更多学术关键词（背景/方法/结果/讨论等）。
        """
        self.config = config or default_config
        self.logger = self.config.logger
        self.scene = scene
        self.parser = TextParser(self.config, scene=scene)
        self.paginator = SmartPaginator(self.config)
        self.generator = PPTXGenerator(self.config)

        self.logger.info(f"PPT Agent 初始化完成 (scene={scene})")

    def generate(self, user_input: str, output_path: str = "output.pptx") -> str:
        """
        根据用户输入生成PPT

        Args:
            user_input: 用户输入的文本内容
            output_path: 输出文件路径

        Returns:
            生成的PPT文件路径
        """
        self.logger.info(f"开始生成PPT，输出路径: {output_path}")

        # 1. 解析文本
        self.logger.debug("步骤1: 解析用户输入...")
        parsed_data = self.parser.parse(user_input)
        self.logger.debug(f"解析完成，共 {len(parsed_data.sections)} 个章节")

        # 验证解析结果
        warnings = self.parser.validate(parsed_data)
        for warning in warnings:
            self.logger.warning(warning)

        # 2. 智能分页
        self.logger.debug("步骤2: 智能分页...")
        pages = self.paginator.paginate(parsed_data)
        self.logger.debug(f"分页完成，共 {len(pages)} 页")

        # 2.5 质量门禁：检测解析是否成功
        content_pages = [
            p for p in pages if p.page_type not in ("cover", "ending", "toc")
        ]
        if len(content_pages) == 0:
            raise ValueError(
                "解析失败：未检测到任何章节内容。\n"
                "请确保输入格式正确：\n"
                "  主题：标题\n"
                "  1. 章节名\n"
                "  - 要点\n"
                "注意：章节标题必须用 '数字.' 开头（如 '1. 教育背景'），不能用 '##' markdown格式"
            )

        # 3. 生成PPT
        self.logger.debug("步骤3: 生成PPT文件...")
        output_file = self.generator.generate(pages, output_path)

        self.logger.info(f"PPT生成成功: {output_file}")
        return output_file

    def generate_from_structured(
        self, data: Dict, output_path: str = "output.pptx"
    ) -> str:
        """
        从结构化数据生成PPT

        Args:
            data: 结构化数据字典
            output_path: 输出文件路径

        Returns:
            生成的PPT文件路径
        """
        self.logger.info(f"从结构化数据生成PPT，输出路径: {output_path}")

        # 将字典转换为ParsedData
        parsed_data = self._dict_to_parsed_data(data)

        # 智能分页
        pages = self.paginator.paginate(parsed_data)

        # 生成PPT
        output_file = self.generator.generate(pages, output_path)

        self.logger.info(f"PPT生成成功: {output_file}")
        return output_file

    def _dict_to_parsed_data(self, data: Dict) -> ParsedData:
        """将字典转换为ParsedData"""
        from .models import CoverData

        parsed = ParsedData()

        if "meta" in data:
            meta = data["meta"]
            parsed.meta = CoverData(
                title=meta.get("title", ""),
                subtitle=meta.get("subtitle", ""),
                author=meta.get("author", ""),
                advisor=meta.get("advisor", ""),
                direction=meta.get("direction", ""),
                date=meta.get("date", ""),
            )

        return parsed

    def preview(self, user_input: str) -> List[Dict]:
        """
        预览生成的页面结构（不生成文件）

        Args:
            user_input: 用户输入的文本内容

        Returns:
            页面结构列表
        """
        self.logger.info("开始预览页面结构...")

        # 解析
        parsed_data = self.parser.parse(user_input)

        # 分页
        pages = self.paginator.paginate(parsed_data)

        # 转换为预览格式
        preview = []
        for i, page in enumerate(pages):
            preview.append(
                {
                    "page_num": i + 1,
                    "page_type": page.page_type,
                    "title": getattr(page.data, "title", "")
                    or getattr(page.data, "part_title", ""),
                    "items_count": len(getattr(page.data, "items", []) or []),
                }
            )

        self.logger.info(f"预览完成，共 {len(preview)} 页")
        return preview


# 便捷函数
def create_ppt(user_input: str, output_path: str = "output.pptx") -> str:
    """
    便捷函数：创建PPT

    Args:
        user_input: 用户输入
        output_path: 输出路径

    Returns:
        生成的PPT文件路径
    """
    agent = PPTAgent()
    return agent.generate(user_input, output_path)
