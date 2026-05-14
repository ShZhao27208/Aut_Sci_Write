"""
组会汇报工作流：
Step1: generate_outline() - 从PDF提取内容+图片，生成提纲Markdown文件
Step2: 用户修改提纲md文件
Step3: build_from_outline() - 根据提纲+已提取图片生成最终PPT
"""

import fitz
import os
import re
from typing import List, Dict, Optional, Tuple
from .config import get_config_value
from .pdf_extractor import PDFFigureExtractor, ExtractedFigure
from .models import (
    FigurePlaceholder,
    ContentWithFigureData,
    ContentListData,
    ContentDetailData,
    ListItem,
    Page,
    PAGE_TYPE_CONTENT_WITH_FIG,
    PAGE_TYPE_CONTENT_LIST,
    PAGE_TYPE_CONTENT_DETAIL,
)


def _call_llm(prompt: str) -> str:
    """通过 Moonshot API 调用 LLM"""
    import json, urllib.request

    api_key = get_config_value("MOONSHOT_API_KEY")
    if not api_key:
        raise ValueError(
            "MOONSHOT_API_KEY is not configured. Add it to skills/sci-ppt/.env "
            "to enable translation."
        )
    payload = json.dumps(
        {
            "model": "moonshot-v1-8k",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.moonshot.cn/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        r = json.loads(resp.read())
        return r["choices"][0]["message"]["content"].strip()


def _translate_to_chinese(text: str) -> str:
    """调用 LLM 将英文学术内容翻译为中文，失败时返回原文。"""
    try:
        return _call_llm(
            "请将以下英文学术内容翻译成简洁的中文，直接输出译文，不要任何解释：\n\n"
            + text
        )
    except Exception as e:
        print(f"  ⚠️  翻译失败（{e}），保留原文")
        return text


def _translate_sections(sections: List[Dict]) -> List[Dict]:
    """将章节标题和要点批量翻译为中文（一次 API 调用）"""
    try:
        lines = []
        for i, sec in enumerate(sections):
            lines.append(f"[SEC{i}]{sec['title']}")
            for j, item in enumerate(sec.get("items", [])):
                lines.append(f"[S{i}I{j}]{item}")

        batch = "\n".join(lines)
        translated = _call_llm(
            "请将以下英文学术内容翻译成中文，保留每行的标签前缀（如[SEC0]、[S0I0]），直接输出，不要解释：\n\n"
            + batch
        )

        result_sections = [dict(s) for s in sections]
        for s in result_sections:
            s["items"] = list(s.get("items", []))

        for line in translated.splitlines():
            m = re.match(r"\[SEC(\d+)\](.+)", line.strip())
            if m:
                idx = int(m.group(1))
                if idx < len(result_sections):
                    result_sections[idx]["title"] = m.group(2).strip()
                continue
            m2 = re.match(r"\[S(\d+)I(\d+)\](.+)", line.strip())
            if m2:
                si, ii = int(m2.group(1)), int(m2.group(2))
                if si < len(result_sections):
                    items = result_sections[si].get("items", [])
                    if ii < len(items):
                        result_sections[si]["items"][ii] = m2.group(3).strip()
        return result_sections
    except Exception as e:
        print(f"  ⚠️  批量翻译失败（{e}），保留原文")
        return sections


# ══════════════════════════════════════════════
#  Step 1: 从 PDF 提取文本+图片，生成提纲 Markdown 文件
# ══════════════════════════════════════════════


def generate_outline(pdf_path: str, output_dir: str = None) -> str:
    """
    读取 PDF，提取全文关键信息，同步提取所有图片，
    生成标准提纲 Markdown 文件（含图片预览）。

    返回：生成的 .md 文件路径（供用户修改）
    """
    doc = fitz.open(pdf_path)
    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # 输出目录：pdf同级目录下的 <pdf名>_outline/
    if output_dir is None:
        output_dir = os.path.join(pdf_dir, f"{pdf_name}_outline")
    figures_dir = os.path.join(output_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    # ── 1. 提取全文文本 ──────────────────────────────
    full_text = ""
    page_texts = []
    for i in range(len(doc)):
        t = doc[i].get_text()
        page_texts.append(t)
        full_text += t

    # ── 2. 提取基本信息 ──────────────────────────────
    title = _extract_title(doc[0].get_text())

    # ── 3. 同步提取所有图片（智能裁切，PyMuPDF坐标渲染）────
    print("  📷 提取PDF图片中...")
    extractor = PDFFigureExtractor(pdf_path, figures_dir)
    all_figures: List[ExtractedFigure] = []
    fig_count = 0
    fig_page_map: Dict[int, List[ExtractedFigure]] = {}  # page_0idx -> [figures]

    for page_0idx in range(len(doc)):
        page = doc[page_0idx]
        imgs = page.get_images(full=True)
        large_imgs = [
            img
            for img in imgs
            if doc.extract_image(img[0]).get("width", 0) > 150
            and doc.extract_image(img[0]).get("height", 0) > 150
        ]
        if not large_imgs:
            continue

        fig_rect = extractor._detect_figure_bbox(page)
        fig_count += 1
        label = f"图{fig_count}"
        filename = f"fig{fig_count}_p{page_0idx + 1}.png"
        out_path = os.path.join(figures_dir, filename)

        try:
            mat = fitz.Matrix(180 / 72, 180 / 72)
            if fig_rect:
                pix = page.get_pixmap(matrix=mat, clip=fig_rect, alpha=False)
            else:
                pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(out_path)
            ef = ExtractedFigure(
                label=label,
                page=page_0idx,
                path=out_path,
                caption=_extract_fig_caption(page_texts[page_0idx], fig_count),
            )
            all_figures.append(ef)
            fig_page_map.setdefault(page_0idx, []).append(ef)
            print(f"    {label}（第{page_0idx + 1}页）→ {filename}")
        except Exception as e:
            print(f"    ⚠️  {label}提取失败：{e}")

    print(f"  ✅ 共提取 {len(all_figures)} 张图片")

    # ── 4. 检测论文章节结构 ──────────────────────────
    sections = _detect_paper_sections(full_text, page_texts)

    # ── 4.5 翻译章节标题和要点为中文 ─────────────────
    print("  🌐 翻译内容为中文...")
    sections = _translate_sections(sections)

    # ── 5. 将图片分配到各章节 ─────────────────────────
    _assign_figures_to_sections(sections, fig_page_map, len(doc))

    # ── 6. 生成 Markdown 文本 ─────────────────────────
    md_lines = [
        f"# 【提纲草稿】请修改后保存，再告诉我生成PPT",
        f"",
        f"> ⚠️ 使用说明：",
        f"> 1. 修改各章节标题和要点内容",
        f"> 2. 图片已自动提取并嵌入，可删除不需要的图片行",
        f"> 3. 图片引用格式 `[图N,页P]` 必须保留（PPT生成器使用）",
        "> 4. 修改完成后保存文件，告诉我「开始生成PPT」",
        f"",
        f"## 基本信息",
        f"- 文章标题：{title}",
        f"- 汇报人：（请填写）",
        f"- 导师：（请填写）",
        f"- 汇报时间：（请填写）",
        f"",
        f"## 提纲结构",
        f"",
    ]

    for sec_idx, sec in enumerate(sections, 1):
        sec_title = sec["title"]
        sec_items = sec.get("items", [])
        sec_figures = sec.get("figures", [])

        md_lines.append(f"### {sec_idx}. {sec_title}")

        # 要点
        if sec_items:
            for item in sec_items:
                md_lines.append(f"- {item}")
        else:
            md_lines.append(f"- （请填写要点）")

        # 图片：预览 + 引用标注
        if sec_figures:
            md_lines.append(f"")
            for ef in sec_figures:
                # 用相对路径，方便markdown预览
                rel_path = os.path.relpath(ef.path, output_dir).replace("\\", "/")
                md_lines.append(f"<!-- 图片预览 -->")
                md_lines.append(f"![{ef.label}]({rel_path})")
                md_lines.append(f"[{ef.label},页{ef.page + 1}]")
                if ef.caption:
                    md_lines.append(f"*图注：{ef.caption}*")

        md_lines.append(f"")

    # 附录：全部图片列表
    if all_figures:
        md_lines += [
            f"---",
            f"## 附录：所有提取图片（供参考）",
            f"",
        ]
        for ef in all_figures:
            rel_path = os.path.relpath(ef.path, output_dir).replace("\\", "/")
            md_lines.append(
                f"- **{ef.label}**（第{ef.page + 1}页）：`[{ef.label},页{ef.page + 1}]`"
            )
            md_lines.append(f"  ![]({rel_path})")
            md_lines.append(f"")

    # ── 7. 保存 .md 文件 ─────────────────────────────
    md_content = "\n".join(md_lines)
    md_path = os.path.join(output_dir, f"{pdf_name}_outline.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"  📝 大纲已保存：{md_path}")
    return md_path


def _extract_title(first_page_text: str) -> str:
    lines = [l.strip() for l in first_page_text.split("\n") if len(l.strip()) > 10]
    return lines[0] if lines else "（未检测到标题）"


def _extract_fig_caption(page_text: str, fig_idx: int) -> str:
    """从页面文本中提取图注（Figure N. 或 Fig. N 格式）"""
    patterns = [
        rf"(?:Figure|Fig\.?)\s*{fig_idx}[\.:]?\s*([^\n]{{5,80}})",
        rf"图\s*{fig_idx}[\.：]?\s*([^\n]{{5,80}})",
    ]
    for pat in patterns:
        m = re.search(pat, page_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _detect_paper_sections(full_text: str, page_texts: List[str]) -> List[Dict]:
    """
    检测论文章节结构，提取各节标题和要点。
    优先识别标准学术论文结构（Introduction/Methods/Results/Discussion/Conclusion）
    """
    # 常见章节关键词（中英文）
    section_keywords = [
        (r"\b(Abstract|摘要)\b", "摘要"),
        (r"\b(Introduction|引言|研究背景)\b", "研究背景与动机"),
        (r"\b(Related Work|Background|相关工作|研究现状)\b", "相关研究"),
        (r"\b(Method|Methods|Methodology|方法|研究方法|实验方案)\b", "研究方法"),
        (r"\b(Materials?|材料|合成)\b", "材料合成与表征"),
        (r"\b(Experiment|Experiments?|实验|实验结果)\b", "实验与结果"),
        (r"\b(Results?|Result|结果|性能)\b", "核心结果"),
        (r"\b(Discussion|讨论|分析)\b", "分析与讨论"),
        (r"\b(Conclusion|Conclusions?|Summary|结论|总结)\b", "总结与展望"),
    ]

    detected = []
    seen_keywords = set()

    # 先检测全文中存在哪些章节
    for pattern, label in section_keywords:
        if re.search(pattern, full_text, re.IGNORECASE) and label not in seen_keywords:
            seen_keywords.add(label)
            # 提取该章节下的要点（简单取第一段有实质内容的句子）
            items = _extract_section_items(full_text, pattern)
            detected.append({"title": label, "items": items, "figures": []})

    # 兜底：如果什么都没检测到，给通用结构
    if not detected:
        detected = [
            {"title": "研究背景与动机", "items": ["（请填写）"], "figures": []},
            {"title": "研究方法", "items": ["（请填写）"], "figures": []},
            {"title": "核心结果", "items": ["（请填写）"], "figures": []},
            {"title": "总结与展望", "items": ["（请填写）"], "figures": []},
        ]

    return detected


def _extract_section_items(full_text: str, section_pattern: str) -> List[str]:
    """提取章节内主要内容，取到下一个章节标题前，最多8条有意义的句子"""
    m = re.search(section_pattern, full_text, re.IGNORECASE)
    if not m:
        return ["（请填写）"]

    start = m.end()
    # 找下一个章节标题的位置（截断点）
    next_section = re.search(
        r"\b(Abstract|Introduction|Related Work|Background|Method|Materials?|"
        r"Experiment|Results?|Discussion|Conclusion|References|摘要|引言|方法|结果|结论)\b",
        full_text[start : start + 3000],
        re.IGNORECASE,
    )
    end = start + next_section.start() if next_section else start + 2000
    snippet = full_text[start:end].strip()

    # 按句切分
    sentences = re.split(r"(?<=[.。!！?？])\s+", snippet)
    items = []
    for s in sentences:
        s = s.strip()
        # 过滤：太短、纯数字引用、图表标注
        if len(s) < 20:
            continue
        if re.match(r"^\[?\d+[\]\.\,]", s):
            continue
        if re.match(r"^(Fig|Figure|Table|Scheme)\s*\d+", s, re.IGNORECASE):
            continue
        # 截断过长的句子，保留前120字符
        items.append(s[:120] + ("..." if len(s) > 120 else ""))
        if len(items) >= 8:
            break

    return items if items else ["（请填写）"]


def _assign_figures_to_sections(
    sections: List[Dict],
    fig_page_map: Dict[int, List[ExtractedFigure]],
    total_pages: int,
):
    """
    将提取的图片按页码比例分配到各章节。
    策略：按章节在论文中大致占的页码范围分配。
    """
    if not fig_page_map or not sections:
        return

    n_sec = len(sections)
    pages_per_sec = total_pages / n_sec

    for page_0idx, figures in sorted(fig_page_map.items()):
        # 估算该页属于哪个章节
        sec_idx = min(int(page_0idx / pages_per_sec), n_sec - 1)
        sections[sec_idx]["figures"].extend(figures)


# ══════════════════════════════════════════════
#  Step 3: 解析用户修改后的提纲，生成 PPT 输入
# ══════════════════════════════════════════════


def parse_outline_to_ppt_input(
    outline: str, pdf_path: str, output_dir: str = "figures"
) -> Tuple[str, Dict[str, str]]:
    """
    解析用户修改后的提纲 Markdown，提取图片路径，
    返回 (ppt_text_input, fig_label_to_path_dict)

    优先策略：
    1. 读取 md 里 ![图N](path) 格式 → 图片已提取，直接用路径，不重复截图
    2. 兜底：遇到 [图N,页P] 且路径不存在时，才从 PDF 重新截图
    """
    outline_dir = os.path.dirname(os.path.abspath(pdf_path)) if pdf_path else "."
    label_to_path: Dict[str, str] = {}

    # ── 1. 优先读取 ![图N](path) 格式（generate_outline 已提取好的图）────
    for m in re.finditer(r"!\[([^\]]+)\]\(([^)]+)\)", outline):
        label = m.group(1).strip()
        rel_path = m.group(2).strip()
        # 路径可能是相对于 md 文件的，转为绝对路径
        abs_path = (
            os.path.join(output_dir, rel_path)
            if not os.path.isabs(rel_path)
            else rel_path
        )
        if os.path.exists(abs_path):
            label_to_path[label] = abs_path
        elif os.path.exists(rel_path):
            label_to_path[label] = os.path.abspath(rel_path)

    # ── 2. 兜底：[图N,页P] 且该图还没有路径时，从 PDF 重新截图 ────────
    fig_refs = re.findall(r"\[([图表Fig\.]+\d*)[,，]页?(\d+)\]", outline)
    missing_fig_map: Dict[str, int] = {}
    for label, page_str in fig_refs:
        if label not in label_to_path:
            missing_fig_map[label] = int(page_str)

    if missing_fig_map and pdf_path and os.path.exists(pdf_path):
        print(f"  ⚠️  {len(missing_fig_map)} 张图未找到本地文件，从PDF重新截取...")
        extractor = PDFFigureExtractor(pdf_path, output_dir)
        extracted = extractor.extract_named_figures(missing_fig_map, dpi=180)
        for ef in extracted:
            label_to_path[ef.label] = ef.path

    # ── 3. 把提纲转为 aut_sci_ppt 的文本格式 ──────────────────────────
    ppt_text = _outline_to_ppt_text(outline, label_to_path)

    return ppt_text, label_to_path


def _outline_to_ppt_text(outline: str, label_to_path: Dict[str, str]) -> str:
    """将提纲 Markdown 转为 aut_sci_ppt 识别的文本格式"""
    lines_out = []
    section_num = 0

    # 提取基本信息
    title = _re_extract(outline, r"文章标题[：:]\s*(.+)")
    author = _re_extract(outline, r"汇报人[：:]\s*(.+)")
    advisor = _re_extract(outline, r"导师[：:]\s*(.+)")
    date = _re_extract(outline, r"汇报时间[：:]\s*(.+)")

    if title:
        lines_out.append(f"主题：{title}")
    if author:
        lines_out.append(f"汇报人：{author}")
    if advisor:
        lines_out.append(f"导师：{advisor}")
    if date:
        lines_out.append(f"时间：{date}")
    lines_out.append("")

    # 解析各节
    current_section = None
    current_items = []
    current_figs = []

    for line in outline.split("\n"):
        # 章节标题
        m = re.match(r"###\s*(\d+)\.\s*(.+)", line)
        if m:
            if current_section:
                lines_out += _flush_section(
                    section_num,
                    current_section,
                    current_items,
                    current_figs,
                    label_to_path,
                )
            section_num += 1
            current_section = m.group(2).strip()
            current_items = []
            current_figs = []
            continue

        # 图片引用
        figs_in_line = re.findall(r"\[([图表Fig\.]+\d*)[,，]页?(\d+)\]", line)
        for label, _ in figs_in_line:
            if label in label_to_path:
                current_figs.append(label)
        if figs_in_line:
            continue

        # 列表项
        m2 = re.match(r"-\s+(.+)", line)
        if m2 and current_section:
            item = m2.group(1).strip()
            if "（请填写）" not in item and item:
                current_items.append(item)

    # flush 最后一节
    if current_section:
        lines_out += _flush_section(
            section_num, current_section, current_items, current_figs, label_to_path
        )

    return "\n".join(lines_out)


def _flush_section(num, title, items, figs, label_to_path):
    lines = [f"\n{num}. {title}"]
    for item in items:
        lines.append(f"- {item}")
    # 图片注释嵌入（后续 parser 识别）
    for label in figs:
        path = label_to_path.get(label, "")
        lines.append(f"<!-- 图: {label} | path={path} | position=right -->")
    return lines


def _re_extract(text: str, pattern: str) -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else ""


# ══════════════════════════════════════════════
#  全自动入口：PDF → PPT（Agent 专用，跳过用户编辑步骤）
# ══════════════════════════════════════════════


def auto_generate_ppt(
    pdf_path: str,
    output_path: str = None,
    author: str = "",
    advisor: str = "",
    date: str = "",
    direction: str = "",
) -> str:
    """
    全自动：PDF → PPT，跳过用户编辑提纲步骤。
    Agent 专用入口。

    Args:
        pdf_path: PDF 文件路径
        output_path: 输出 PPT 路径（默认在提纲目录下生成）
        author: 汇报人姓名（替换提纲中的占位符）
        advisor: 导师姓名
        date: 汇报日期
        direction: 研究方向

    Returns:
        生成的 .pptx 文件路径
    """
    from .agent import PPTAgent

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    # Step 1: 生成提纲（自动提取内容+图片+翻译）
    print(f"  ⏳ Step 1/3: 从 PDF 提取内容和图片...")
    md_path = generate_outline(pdf_path)
    print(f"  ✅ 提纲已生成: {md_path}")

    # Step 2: 读取提纲并补充用户信息（不等用户编辑）
    with open(md_path, "r", encoding="utf-8") as f:
        outline_text = f.read()

    # 替换占位符
    if author:
        outline_text = outline_text.replace("汇报人：（请填写）", f"汇报人：{author}")
    if advisor:
        outline_text = outline_text.replace("导师：（请填写）", f"导师：{advisor}")
    if date:
        outline_text = outline_text.replace("汇报时间：（请填写）", f"汇报时间：{date}")

    # Step 3: 解析提纲，关联图片路径
    print(f"  ⏳ Step 2/3: 解析提纲并关联图片...")
    outline_dir = os.path.dirname(md_path)
    figures_dir = os.path.join(outline_dir, "figures")
    ppt_text, label_to_path = parse_outline_to_ppt_input(
        outline_text, pdf_path, output_dir=figures_dir
    )

    # 补充元数据到 ppt_text 头部（如果提纲解析时丢失了）
    meta_lines = []
    if author and f"汇报人：{author}" not in ppt_text:
        meta_lines.append(f"汇报人：{author}")
    if advisor and f"导师：{advisor}" not in ppt_text:
        meta_lines.append(f"导师：{advisor}")
    if date and f"时间：{date}" not in ppt_text:
        meta_lines.append(f"时间：{date}")
    if direction:
        meta_lines.append(f"申请方向：{direction}")
    if meta_lines:
        ppt_text = "\n".join(meta_lines) + "\n" + ppt_text

    # Step 4: 生成 PPT
    if output_path is None:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(outline_dir, f"{pdf_name}_汇报.pptx")

    print(f"  ⏳ Step 3/3: 生成 PPT...")
    agent = PPTAgent()
    result = agent.generate(ppt_text, output_path)
    print(f"  ✅ PPT 生成完成: {result}")
    return result
