<div align="center">
<img src="docs/logo.gif" width="160" height="160" alt="瞾 — Shuo Zhao" style="border-radius:50%;"/>

# Aut_Sci_Write

**Autonomous Scientific Writer**

*A modular Claude Code Skills suite for the full academic research lifecycle*
[![Version](https://img.shields.io/badge/version-1.4.1-2563eb.svg)](package.json)
[![Skills](https://img.shields.io/badge/skills-7-0f766e.svg)](#-what-it-does)
[![Academic Workflow](https://img.shields.io/badge/workflow-search%20%E2%86%92%20extract%20%E2%86%92%20review%20%E2%86%92%20slides-c2410c.svg)](#-what-it-does)
[![Paper Types](https://img.shields.io/badge/papers-research%20%7C%20review%20%7C%20meta--analysis-7c3aed.svg)](#-what-it-does)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![PPTX + HTML](https://img.shields.io/badge/output-PPTX%20%2B%20HTML-0ea5e9.svg)](#-what-it-does)
[![Zotero](https://img.shields.io/badge/reference-Zotero-b91c1c.svg)](#-what-it-does)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ShZhao27208/Aut_Sci_Write?style=social)](https://github.com/ShZhao27208/Aut_Sci_Write)

[🌐 Live Demo](https://shzhao27208.github.io/Aut_Sci_Write/) · [📦 Install](#-installation) · [📖 中文说明](#中文说明)

</div>

---

## English

**Aut_Sci_Write** is a modular collection of **AI Agent Skills** that automates the entire academic research and writing lifecycle — from literature discovery and deep PDF analysis to figure extraction, review writing, and professional PPT generation.

> Install once, use anywhere. Just talk to AI Agent naturally — the skills activate automatically based on what you say.


### ✨ What It Does

| Skill | Description | Example Trigger |
|:------|:------------|:----------------|
| `sci-search` | Search arXiv + PubMed + **Web of Science** simultaneously with JCR tier & impact factor data | /sci-search *Find high-IF papers on perovskite solar cells* |
| `sci-extract` | Extract core insights, experimental parameters, and conclusions from PDFs | /sci-extract  *Analyze the key findings of paper.pdf* |
| `sci-figure` | Auto-detect and crop figures from PDFs at 600 DPI, with subfigure splitting | /sci-figure *Extract Figure 3c from this paper* |
| `sci-review` | Draft literature reviews and professional peer-review rebuttals (NeurIPS/ICLR standard) | /sci-figure *Write a literature review on GNNs for drug discovery* |
| `sci-zotero` | Sync Zotero library, add citations by DOI/ISBN/PMID, fetch open-access PDFs | /sci-zotero *Connect to my Zotero database* |
| `sci-ppt` | Generate professional academic PPTX from paper PDFs or structured text, with LaTeX formula rendering | /sci-zotero *Turn this paper into a seminar presentation* |
| `sci-html` | Convert PDFs, Markdown, outlines, or summaries into interactive academic HTML slide decks and browser reports. | /sci-html Turn this paper into an interactive HTML report |

### 🚀 Installation

**Prerequisites**

Before installation, make sure the following environments are available:

- **Python 3.10+**: required for Python-based skills such as `sci-search`, `sci-extract`, `sci-figure`, `sci-review`, and `sci-ppt`
- **Node.js 18+**: required for `npx skills add ...` installation and CLI-based skill registration
- **pip**: used to install Python dependencies from `requirements.txt`

**One-line install** (***Recommended*** — installs all 7 skills globally):

```bash
npx skills add ShZhao27208/Aut_Sci_Write -g -y
```

**Update to latest version:**

```bash
npx skills add ShZhao27208/Aut_Sci_Write -g -y
```

**Manual install** (clone and install Python dependencies):

```bash
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write
pip install -r requirements.txt
```

**OR**（Download/Clone to local and use the npm command）：

```bash
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write
npx skills add . -g -y
```

### ⚙️ Configuration

Run the initializer after installation:

```bash
aut-sci-write-init-env
```

Then fill the generated skill-local `.env` files where needed. Do not commit or publish `.env` files.
Do not store API keys in system environment variables unless you intentionally want a machine-wide fallback.

> **Shared keys:** After filling a key, run `aut-sci-write-init-env` again. The initializer copies any shared key (e.g. `ZOTERO_API_KEY`) into every other skill that declares it, so you only fill it once. If the same key is set to different values in two skills, the first one (by skill order) is kept and a warning is printed.

```bash
# For sci-zotero (optional)
ZOTERO_API_KEY=your_personal_api_key
ZOTERO_USER_ID=your_numeric_user_id

# For sci-search — Web of Science (optional but recommended)
# Apply for a free key at: https://developer.clarivate.com/apis/wos-starter
WOS_API_KEY=your_wos_api_key

# For sci-ppt PDF workflow (choose one)
ANTHROPIC_API_KEY=sk-ant-...    # Claude API
MOONSHOT_API_KEY=sk-...         # Moonshot API

# For sci-figure subfigure OCR (optional, Windows example)
TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

> Get your Zotero API key at: https://www.zotero.org/settings/keys
> Get your Web of Science API key at: https://developer.clarivate.com/apis

### 💬 Usage Examples

Once installed, just type naturally in AI Agent — no commands to memorize:

```
# Literature search
"/sci-search Search for recent papers on solid-state electrolytes for lithium batteries"

# Deep paper analysis
"/sci-extract Extract the core findings and experimental parameters from paper.pdf"

# Figure extraction
"/sci-figure Extract Figure 3 from paper.pdf and split subfigures a, b, c"

# Literature review
"/sci-review Write a literature review on graph neural networks in drug discovery"

# Rebuttal writing
"/sci-review Help me respond to Reviewer 2's comment about missing baselines"

# Zotero sync
"/sci-zotero List the paper items from my Zotero 'Materials' collection"

# PPT generation
"/sci-ppt Convert paper.pdf into a group meeting presentation, save as seminar.pptx"

# HTML report generation
"/sci-html Convert paper.pdf into an interactive browser-based academic report"
```

### 📁 Repository Structure

```
Aut_Sci_Write/
├── skills/
│   ├── sci-search/     # Literature search with journal metrics
│   ├── sci-extract/    # Paper analysis and structured insight extraction
│   ├── sci-figure/     # PDF figure and subfigure extraction
│   ├── sci-review/     # Literature review and rebuttal writing
│   ├── sci-ppt/        # Academic PPTX generation 
│   ├── sci-html/       # Interactive HTML reports and browser slide decks
│   └── sci-zotero/     # Zotero library integration
├── scripts/
│   ├── extract_core_insights.py  # Compatibility wrapper for sci-extract CLI
│   ├── zotero.py                 # Compatibility wrapper for sci-zotero CLI
│   └── journal_db.json           # Journal metrics database (independently updatable)
├── examples/                 # Sample outputs (PDF + Markdown + PPT)
├── docs/                     # GitHub Pages site
├── init-env.js         # Per-skill .env initializer
├── skills-cli.js       # Local skill discovery helper
└── requirements.txt    # Shared Python dependencies
```

### 🤝 Contributing

Contributions welcome! Priority areas:
- Add journal metrics to `scripts/journal_db.json`
- Add writing templates to `skills/sci-review/templates/`
- Add new PPT slide types to `skills/Aut_Sci_PPt/src/aut_sci_ppt/templates/`
- Post problems you encounter  when using it to `issue`

---







## 中文说明

**Aut_Sci_Write** 是一套专为科研工作者设计的 **AI Agent Skills 技能包**，将科研写作的各个环节自动化，覆盖从文献发现到成果输出的完整链路。

> 安装一次，随处可用。直接用自然语言和 AI Agent 对话，技能会根据你说的内容自动激活。

### ✨ 功能概览

| 技能 | 功能描述 | 触发词示例 |
|------|----------|:----------|
| `sci-search` | arXiv + PubMed + **Web of Science** 三源检索，自动附加 JCR 分区和影响因子 | /sci-search *搜索钙钛矿太阳能电池最新论文* |
| `sci-extract` | 从 PDF 提取核心发现、实验参数、数值对比和主要结论 | /sci-extract *分析 paper.pdf 的核心结论* |
| `sci-figure` | 自动检测并裁剪论文图片（600 DPI），支持复合图拆分为子图 | /sci-figure *提取论文第3张图的子图* |
| `sci-review` | 文献综述写作 + 专业审稿回复，对标 NeurIPS/ICLR 标准 | /sci-review *帮我写图神经网络在药物发现中的综述* |
| `sci-zotero` | Zotero 文献库同步，支持 DOI/ISBN/PMID 添加引用，自动获取 PDF | /sci-zotero *连接我的zotero数据库* |
| `sci-ppt` | 从论文 PDF 或结构化文本一键生成学术 PPT，支持 LaTeX 公式渲染 | /sci-ppt *把这篇文献做成组会汇报PPT* |
| `sci-html` | 将论文 PDF、Markdown、大纲或总结转换为可交互的 HTML 学术报告或浏览器幻灯片。 | /sci-html 把这篇论文做成网页版交互报告 |

### 🚀 安装方法

**安装前提**

安装前请先确保本机已具备以下环境：

- **Python 3.10 及以上**：用于运行 `sci-search`、`sci-extract`、`sci-figure`、`sci-review`、`sci-ppt` 等基于 Python 的技能
- **Node.js 18 及以上**：用于执行 `npx skills add ...` 安装命令，以及完成 CLI 方式的技能注册
- **pip**：用于安装 `requirements.txt` 中的 Python 依赖

**一行命令安装**（***推荐***，将全部 7 个技能进行全局安装）：

```bash
npx skills add ShZhao27208/Aut_Sci_Write -g -y 
```

**更新到最新版本**（重新运行安装命令即可覆盖更新）：

```bash
npx skills add ShZhao27208/Aut_Sci_Write -g -y 
```

**手动安装**（克隆仓库并安装 Python 依赖）：

```bash
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write
pip install -r requirements.txt
```

**或者**（下载/克隆到本地使用npm命令）：

```bash
git clone https://github.com/ShZhao27208/Aut_Sci_Write.git
cd Aut_Sci_Write
npx skills add . -g -y
```

### Skill-local `.env` configuration

Run `aut-sci-write-init-env` after installation, then put keys in each skill-local `.env` file:

> **共享密钥：** 填好密钥后，请再次运行 `aut-sci-write-init-env`。初始化器会把共享密钥（如 `ZOTERO_API_KEY`）自动复制到所有声明了该密钥的其他 skill，因此只需填一次。若同一密钥在两个 skill 中填了不同的值，将保留靠前的那个（按 skill 顺序）并打印警告。

```bash
# sci-zotero 文献管理（可选）
ZOTERO_API_KEY=你的个人API密钥
ZOTERO_USER_ID=你的Zotero数字用户ID

# sci-search Web of Science 检索（可选，强烈推荐）
# 免费申请地址：https://developer.clarivate.com/apis/wos-starter
WOS_API_KEY=你的WoS_API密钥

# sci-ppt 论文工作流（选择其一）
ANTHROPIC_API_KEY=sk-ant-...    # Claude API
MOONSHOT_API_KEY=sk-...         # Moonshot API（国内推荐）

# sci-figure 子图 OCR 识别（可选）
# Windows 示例：
TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

> Zotero API Key 获取地址：https://www.zotero.org/settings/keys
> Web of Science API Key 申请地址：https://developer.clarivate.com/apis

### 💬 使用示例

安装后直接在AI Agent 中用自然语言对话，无需记忆命令：

```
# 文献检索
"/sci-search 搜索关于锂离子电池固态电解质的高影响因子论文"

# 深度论文解析
"/sci-extract 分析 paper.pdf 的核心发现，提取实验参数和主要结论"

# 图表提取
"/sci-figure 从 paper.pdf 中提取 Figure 3 并拆分子图 a、b、c"

# 文献综述
"/sci-review 帮我写一篇关于图神经网络在药物发现中应用的文献综述"

# 审稿回复
"/sci-review 帮我回复审稿人2关于缺少基线对比实验的意见"

# Zotero 同步
"/sci-zotero 列出我 Zotero 中 Materials 文件夹的文献条目"

# 生成 PPT
"/sci-ppt 把 paper.pdf 做成组会汇报PPT，输出到 seminar.pptx"

# 生成 HTML汇报
"/sci-html 将 paper.pdf 转换成交互式 HTML 学术报告"
```

### 📁 项目结构

```
Aut_Sci_Write/
├── skills/
│   ├── sci-search/           # 文献检索与期刊指标
│   ├── sci-extract/          # 文献核心内容提取
│   ├── sci-figure/           # 论文图表检测与裁剪
│   ├── sci-review/           # 综述写作与审稿回复
│   ├── sci-ppt/              # PPT 生成引擎（模板、布局、解析器）
│   ├── sci-html/             # html交互式报告生成
│   └── sci-zotero/           # Zotero 文献库集成
├── scripts/
│   ├── extract_core_insights.py  # sci-extract CLI 兼容包装
│   ├── zotero.py                 # sci-zotero CLI 兼容包装
│   └── journal_db.json       # 期刊指标数据库（可独立更新）
├── examples/                 # 示例输出（PDF + Markdown + PPT）
├── docs/                     # GitHub Pages 展示页
├── init-env.js               # 按技能划分的.env 初始化器
├── skills-cli.js             # 本地技能发现助手
└── requirements.txt        
```

### 🤝 贡献指南

欢迎贡献！优先方向：
- 在 `scripts/journal_db.json` 中补充期刊指标数据
- 在 `skills/sci-review/templates/` 中添加新的写作模板
- 在 `skills/Aut_Sci_PPt/src/aut_sci_ppt/templates/` 中新增 PPT 页面类型
- 在`issue`中提出自己遇到的问题

![examles](./examples/examples.png)

---

## 📄 License

MIT License — see [LICENSE](LICENSE)



## Star History

<a href="https://www.star-history.com/?repos=ShZhao27208%2FAut_Sci_Write&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=ShZhao27208/Aut_Sci_Write&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=ShZhao27208/Aut_Sci_Write&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=ShZhao27208/Aut_Sci_Write&type=date&legend=top-left" />
 </picture>
</a>
