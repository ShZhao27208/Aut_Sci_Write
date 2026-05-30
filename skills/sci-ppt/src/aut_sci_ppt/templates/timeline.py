"""
时间线页 - 科研汇报风格：横向时间轴 + 节点圆圈 + 内容卡片
"""
from .base import BaseTemplate, hex_to_rgb
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN


class TimelineTemplate(BaseTemplate):
    def render(self, data):
        self.draw_nav_sidebar()
        cx = self.CONTENT_X
        cw = self.W - cx - 0.25

        title    = getattr(data, "title", "")
        events   = getattr(data, "events", []) or []
        part_num = getattr(data, "part_num", "")

        self.draw_header_bar(part_num=part_num, title=title)

        if not events:
            return

        n = len(events)

        # ── 时间轴主线（水平居中）──────────────────────────
        AXIS_TOP  = 3.6     # 时间轴 y 坐标
        AXIS_LEFT = cx + 0.3
        AXIS_W    = cw - 0.5

        # 主轴线（深蓝）
        self.add_line(AXIS_LEFT, AXIS_TOP, AXIS_W,
                      color=self.COLOR_PRIMARY, width_pt=2.5)

        # 每个节点的 x 坐标（等间距）
        if n == 1:
            xs = [AXIS_LEFT + AXIS_W / 2]
        else:
            xs = [AXIS_LEFT + i * AXIS_W / (n - 1) for i in range(n)]

        NODE_R = 0.18   # 节点圆半径（英寸）

        for i, event in enumerate(events):
            x     = xs[i]
            date  = getattr(event, "date",        "") or (event.get("date", "") if isinstance(event, dict) else "")
            etitle= getattr(event, "title",       "") or (event.get("title", "") if isinstance(event, dict) else "")
            desc  = getattr(event, "description", "") or (event.get("description", "") if isinstance(event, dict) else "")

            # ── 节点圆圈 ──
            self.add_rect(
                x - NODE_R, AXIS_TOP - NODE_R,
                NODE_R * 2, NODE_R * 2,
                fill_color=self.COLOR_PRIMARY
            )
            # 内圆（金色）
            inner = NODE_R * 0.55
            self.add_rect(
                x - inner, AXIS_TOP - inner,
                inner * 2, inner * 2,
                fill_color=self.COLOR_GOLD
            )

            # ── 奇偶交替：上下布局 ──
            is_up = (i % 2 == 0)

            if is_up:
                # 内容卡片在轴上方
                card_top    = AXIS_TOP - 2.55
                card_h      = 2.2
                stem_top    = AXIS_TOP - 0.35
                stem_bottom = card_top + card_h
            else:
                # 内容卡片在轴下方
                card_top    = AXIS_TOP + 0.35
                card_h      = 2.2
                stem_top    = card_top
                stem_bottom = AXIS_TOP + 0.35

            # 连接竖线
            self.slide.shapes.add_connector(
                1,
                Inches(x), Inches(min(stem_top, stem_bottom)),
                Inches(x), Inches(max(stem_top, stem_bottom))
            ).line.color.rgb = hex_to_rgb(self.COLOR_PRIMARY)

            card_w = min(AXIS_W / n - 0.15, 2.8)
            card_left = x - card_w / 2

            # 卡片背景（淡蓝底）
            self.add_rect(card_left, card_top, card_w, card_h,
                          fill_color="EEF4FB", line_color="C5D8EE")

            # 顶部深蓝色条（卡片头）
            self.add_rect(card_left, card_top, card_w, 0.36,
                          fill_color=self.COLOR_PRIMARY)

            # 日期（白色，卡片头）
            if date:
                self.add_textbox(card_left + 0.05, card_top + 0.03,
                    card_w - 0.1, 0.32,
                    text=str(date), font_name=self.FONT_EN,
                    font_size=13, bold=True, color=self.COLOR_WHITE,
                    align=PP_ALIGN.CENTER)

            # 事件标题（深蓝加粗）
            if etitle:
                self.add_textbox(card_left + 0.08, card_top + 0.4,
                    card_w - 0.16, 0.48,
                    text=str(etitle), font_name=self.FONT_CN,
                    font_size=14, bold=True, color=self.COLOR_PRIMARY,
                    align=PP_ALIGN.CENTER, wrap=True)

            # 描述（黑色正文）
            if desc:
                self.add_textbox(card_left + 0.08, card_top + 0.9,
                    card_w - 0.16, card_h - 1.0,
                    text=str(desc), font_name=self.FONT_CN,
                    font_size=12, bold=False, color=self.COLOR_BLACK,
                    align=PP_ALIGN.LEFT, wrap=True)
