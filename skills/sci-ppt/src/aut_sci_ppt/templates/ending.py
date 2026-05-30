"""结尾页 - 整体优化版"""
from .base import BaseTemplate
from pptx.enum.text import PP_ALIGN

class EndingTemplate(BaseTemplate):
    def render(self, data):
        # 深蓝全背景
        self.add_rect(0, 0, self.W, self.H, fill_color=self.COLOR_PRIMARY)
        # 顶底金线
        self.add_rect(0, 0, self.W, 0.09, fill_color=self.COLOR_GOLD)
        self.add_rect(0, self.H - 0.09, self.W, 0.09, fill_color=self.COLOR_GOLD)
        # 左右竖条装饰
        self.add_rect(0, 0, 0.12, self.H, fill_color="0D1E35")
        self.add_rect(self.W - 0.12, 0, 0.12, self.H, fill_color="0D1E35")

        message = getattr(data, "message", "感谢聆听，请批评指正！")
        author  = getattr(data, "author", "")
        advisor = getattr(data, "advisor", "")

        # 感谢语
        self.add_textbox(1.0, 2.5, 11.3, 1.3,
            text=message, font_name=self.FONT_CN, font_size=36,
            bold=True, color=self.COLOR_WHITE, align=PP_ALIGN.CENTER)

        # 双装饰线
        self.add_line(3.5, 4.0, 6.3, color=self.COLOR_GOLD, width_pt=2.0)
        self.add_line(4.2, 4.18, 4.9, color="3D6A99", width_pt=0.8)

        # 汇报人信息
        info = []
        if author:  info.append(f"汇报人：{author}")
        if advisor: info.append(f"指导教师：{advisor}")
        if info:
            self.add_textbox(1.0, 4.35, 11.3, 0.65,
                text="    ".join(info), font_name=self.FONT_KAI,
                font_size=18, bold=True, color="8BAFD4",
                align=PP_ALIGN.CENTER)
