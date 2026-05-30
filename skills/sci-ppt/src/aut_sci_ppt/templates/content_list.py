"""
内容列表页 - 终版：溢出保护 + 填满页面
算法：二分法找最大字号，使总高度 <= FOOT_Y，再均匀分配间距
"""
from .base import BaseTemplate, hex_to_rgb
from pptx.util import Inches, Pt
from pptx.oxml.ns import qn
from lxml import etree
import re


def _set_lnsp(tf, pt_val):
    for para in tf.paragraphs:
        pPr = para._p.get_or_add_pPr()
        el = pPr.find(qn("a:lnSpc"))
        if el is None: el = etree.SubElement(pPr, qn("a:lnSpc"))
        sp = el.find(qn("a:spcPts"))
        if sp is None: sp = etree.SubElement(el, qn("a:spcPts"))
        sp.set("val", str(int(pt_val * 100)))


def _calc(texts, avail_h, cw):
    """返回 (font_size, [item_heights]) 保证 sum(heights) <= avail_h"""
    for fs in range(22, 9, -1):
        cpl = max(1, int((cw - 0.18) * 72 / (fs * 0.58)))
        heights = [fs / 72 * 1.28 * max(1, -(-len(t) // cpl)) + 0.06 for t in texts]
        if sum(heights) <= avail_h:
            return fs, heights
    fs = 9
    cpl = max(1, int((cw - 0.18) * 72 / (fs * 0.58)))
    heights = [fs / 72 * 1.28 * max(1, -(-len(t) // cpl)) + 0.06 for t in texts]
    return fs, heights


class ContentListTemplate(BaseTemplate):
    HEADER_Y = 0.68
    FOOT_Y   = 7.28   # 距页底留约半行

    def render(self, data):
        self.draw_nav_sidebar()
        cx = self.CONTENT_X
        cw = self.W - cx - 0.22

        title    = getattr(data, "title",    "")
        subtitle = getattr(data, "subtitle", "")
        items    = getattr(data, "items",    []) or []
        part_num = getattr(data, "part_num", "")

        self.draw_header_bar(part_num=part_num, title=title)

        y = self.HEADER_Y + 0.12
        if subtitle:
            self.add_textbox(cx + 0.1, y, cw - 0.1, 0.30,
                text=subtitle, font_name=self.FONT_CN,
                font_size=11, color=self.COLOR_PRIMARY)
            y += 0.32
        self.add_line(cx, y, cw, color=self.COLOR_PRIMARY, width_pt=0.9)
        y += 0.15

        if not items: return

        avail_h = self.FOOT_Y - y
        texts   = [item.text if hasattr(item, "text") else str(item) for item in items]
        fs, heights = _calc(texts, avail_h, cw)

        total   = sum(heights)
        gap     = max(0, avail_h - total) / len(texts)  # 均匀间距
        line_sp = fs * 1.28

        for i, text in enumerate(texts):
            box_h = heights[i] + gap
            tb = self.slide.shapes.add_textbox(
                Inches(cx + 0.05), Inches(y),
                Inches(cw - 0.05), Inches(box_h))
            tf = tb.text_frame; tf.word_wrap = True
            _set_lnsp(tf, line_sp)
            p = tf.paragraphs[0]
            r0 = p.add_run(); r0.text = "➢  "
            r0.font.name = self.FONT_EN; r0.font.size = Pt(fs)
            r0.font.color.rgb = hex_to_rgb(self.COLOR_PRIMARY)
            self._render_rich(p, text.strip(), fs)
            y += box_h

    def _render_rich(self, paragraph, text, size=14):
        for part in re.split(r"(\*\*.*?\*\*)", text):
            if part.startswith("**") and part.endswith("**"):
                r = paragraph.add_run(); r.text = part[2:-2]
                r.font.name = self.FONT_EN; r.font.size = Pt(size)
                r.font.bold = True
                r.font.color.rgb = hex_to_rgb(self.COLOR_RED)
            elif part:
                r = paragraph.add_run(); r.text = part
                r.font.name = self.FONT_EN; r.font.size = Pt(size)
                r.font.color.rgb = hex_to_rgb(self.COLOR_BLACK)
