"""
章节页 - 无导航栏版：全页宽视觉冲击设计
"""
from .base import BaseTemplate
from pptx.enum.text import PP_ALIGN

class SectionTemplate(BaseTemplate):
    def render(self, data):
        # ✅ 不调用 draw_nav_sidebar()，整页全宽设计
        part_num   = getattr(data, "part_num",   "")
        part_title = getattr(data, "part_title", "")

        W, H = self.W, self.H

        # 左侧深蓝竖条（1.2英寸）
        self.add_rect(0, 0, 1.2, H, fill_color=self.COLOR_PRIMARY)
        # 左侧顶部金色块
        self.add_rect(0, 0, 1.2, 0.8, fill_color=self.COLOR_GOLD)
        # 右侧主背景（深蓝渐变感，更有视觉冲击力）
        self.add_rect(1.2, 0, W - 1.2, H, fill_color="D6E4F0")
        # 顶部深蓝细条
        self.add_rect(1.2, 0, W - 1.2, 0.07, fill_color=self.COLOR_PRIMARY)
        # 底部深蓝细条
        self.add_rect(1.2, H - 0.07, W - 1.2, 0.07, fill_color=self.COLOR_PRIMARY)

        center_y = H / 2
        cx = 1.4   # 内容起始 x（紧贴左侧竖条）
        cw = W - cx - 0.3

        # Part N 标签
        if part_num:
            self.add_textbox(cx, center_y - 1.05, cw, 0.55,
                text=f"— Part  {part_num} —",
                font_name=self.FONT_EN, font_size=24,
                bold=True, color=self.COLOR_GOLD,
                align=PP_ALIGN.CENTER)

        # 金色主装饰线
        self.add_line(cx + 1.0, center_y - 0.42, cw - 2.0,
                      color=self.COLOR_GOLD, width_pt=2.5)

        # 大标题（全宽，字号更大）
        if part_title:
            fs = 52 if len(part_title) <= 6 else (44 if len(part_title) <= 10 else 36)
            self.add_textbox(cx, center_y - 0.38, cw, 1.1,
                text=part_title,
                font_name=self.FONT_CN, font_size=fs,
                bold=True, color=self.COLOR_PRIMARY,
                align=PP_ALIGN.CENTER)

        # 蓝色副装饰线
        self.add_line(cx + 1.5, center_y + 0.82, cw - 3.0,
                      color=self.COLOR_PRIMARY, width_pt=1.2)
