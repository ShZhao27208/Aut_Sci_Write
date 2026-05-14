---
name: sci-ppt
description: Generate professional academic PowerPoint (PPTX) presentations from paper PDFs, structured outlines, or plain text. Use for thesis defense, seminar reports, literature presentations, and graduate school applications. Supports automatic figure extraction, LaTeX formula rendering, and bilingual (Chinese/English) layouts.
author: Shuo Zhao         
license: MIT
copyright: © 2026 Shuo Zhao. All rights reserved.   
triggers:
  - 生成PPT
  - 做PPT
  - 制作PPT
  - 演示文稿
  - pptx
  - 汇报
  - 论文转PPT
  - 答辩PPT
  - 开题报告
  - 组会汇报
  - 推免汇报
  - 学术汇报
  - make presentation
  - create slides
  - paper to ppt
---

# Sci-PPT —  Academic Auto-PPT Agent

A specialized tool for generating professional academic presentations directly from paper content or structured outlines.

## Core Behavioral Rules (The 12 Laws)

1. **Format**: Use `1. Title` for chapters and `- Point` for bullets.
2. **Markdown**: 🚫 DO NOT use `##` for slide titles; it is not recognized by the parser.
3. **Innovation**: Identify the core innovation of the paper and highlight it in **Red**.
4. **Imagery**: Use HD extraction (600 DPI) for figures; minimum width >= 300px.
5. **No Scrapping**: 🚫 PROHIBITED to scrap low-quality bitmaps from PDF streams.
6. **Formulas**: Render LaTeX formulas as high-quality transparent PNGs.
7. **Transparency**: All generated formula/media assets must have transparent backgrounds.
8. **Feedback**: Inform the user if an operation (like PDF parsing) will take >10 seconds.
9. **Final Output**: 🚫 DO NOT output intermediate Markdown; generate and provide the `.pptx` directly.
10. **Colors**: Use `#1E3A5F` (Primary Blue) and `#EE0000` (Highlight Red).
11. **Layout**: Ensure zero text-overflow or figure-text overlap.
12. **Professionalism**: Keep communication brief and technical; skip AI pleasantries.

## Usage

### Simple Text Input
```python
from aut_sci_ppt import create_ppt

create_ppt("""
主题：[Title]
申请人：[Name]
1. [Section Title]
- [Content]
""", "output.pptx")
```

### PDF to PPT (Academic Workflow)
```python
from aut_sci_ppt import auto_generate_ppt

output = auto_generate_ppt("paper.pdf", author="张三", advisor="李教授")
```

## Skill-local `.env` values
- `MOONSHOT_API_KEY` (optional): Used for Chinese translation in PDF-to-PPT workflow. If not set, content is kept in original language.
- Network access required for LaTeX formula rendering (via codecogs.com).





---

## © License & Copyright

**Aut_Sci_Write** — Autonomous Scientific Writer

- **Author**: Shuo Zhao
- **License**: MIT License
- **Copyright**: © 2026 Shuo Zhao. All rights reserved.
- **Original Work**: This is an original work created by the author. No reproduction, redistribution, or commercial use without explicit permission.
  **Permission is hereby granted**, free of charge, to any person obtaining a copy of this software... (**See the LICENSE file in the root directory for the full MIT terms.**)

---

*This skill is part of the Aut_Sci_Write suite. For full license terms, see the [LICENSE](../LICENSE) file in the project root.*
---

