# Aut_Sci_PPt

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Aut_Sci_PPt** is an automated agent designed to convert academic papers (PDF) or structured text into professional, presentation-ready PowerPoint files (.pptx). It is specifically optimized for graduate defense, academic seminars, and research proposals.

## ✨ Key Features

- 📄 **PDF Extraction**: Intelligent parsing of academic papers using PyMuPDF.
- 📐 **Smart Layout**: Automatic typography engine that prevents overflow and maintains white space.
- ➗ **LaTeX Support**: Renders complex formulas as high-definition transparent PNGs.
- 🖼️ **HD Figures**: Extracts and embeds figures with high DPI for clarity.
- 🎨 **Academic Theme**: Built-in professional theme following common university standards (Deep Blue & Accent Red).

## 🚀 Quick Start

### Installation

```bash
pip install python-pptx pyyaml pymupdf Pillow
```

### Basic Usage

```python
from aut_sci_ppt import PPTAgent

agent = PPTAgent()
user_input = """
主题：材料学科研究生汇报
申请人：dd
1. 教育背景
- dd
- 绩点: 3.57/4.0
"""
agent.generate(user_input, "presentation.pptx")
```

## 📜 Repository Structure

- `src/aut_sci_ppt/`: Core source code.
- `SKILL.md`: Claude Code skill manifest and behavioral rules.
- `requirements.txt`: Project dependencies.
- `LICENSE`: MIT License.

## 🤝 Contributing

This project is open-sourced to help students and researchers. Feel free to submit issues or pull requests to improve the layout engine and parsing accuracy.

---
© 2026 Aut_Sci_PPT
