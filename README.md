# Aut_Sci_Write: Autonomous Scientific Writer 🚀

**Autonomous Scientific Writer (Aut_Sci_Write)** is a modular collection of **Claude Code Skills** designed to automate the entire academic research and writing lifecycle—from literature discovery and Zotero integration to visual data analysis and high-level manuscript refinement.

Inspired by advanced agentic workflows, this project bridges the gap between raw data (PDFs/Web) and submission-ready scientific content.

---

## 🌟 Core Features

### 1. Unified Paper Search (`sci-search`)
- Search Arxiv and PubMed simultaneously.
- Intelligent ranking using a decoupled **Journal Database** (`scripts/journal_db.json`) providing JCR Tiers, Impact Factors, and publisher info (Nature, Science, Wiley, Elsevier, etc.).
- Local caching in `library.json` for rapid iterative research, with an opt-out flag when running the CLI directly.

### 2. Deep Literature Extraction (`sci-extract` & `sci-zotero`)
- **Core Insights Extraction**: Moves beyond simple summaries to extract experimental parameters, numerical comparisons, and core conclusions.
- **Zotero Sync**: One-click synchronization of your remote Zotero collections directly into your local workspace.
- **Multi-format Support**: Robust handling of PDFs via `pdfplumber` and `PyMuPDF`.

### 3. Visual Figure Intelligence (`sci-figure`)
- **Figure Awareness**: Automatically detect and extract figures from scientific PDFs.
- **Subfigure Splitting**: Intelligent logic to split complex figures (e.g., Figure 1a, 1b, 1c) into individual images for multi-modal analysis by Claude.

### 4. Expert Writing Refinement (`sci-review`)
- **Reference-driven Editing**: High-level guides for writing rebuttals, choosing academic terminology, and structuring complex sections.
- **Context-aware Polishing**: Refine your drafts based on established expert templates.

---

## 🛠️ Quick Start

### 1. Installation
Ensure you have **Claude Code** installed. Then clone this repo:
```bash
git clone https://github.com/your-username/Aut_Sci_Write.git
cd Aut_Sci_Write
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file or set environment variables:
- `ZOTERO_API_KEY`: Your personal Zotero API key.
- `ZOTERO_USER_ID`: Your Zotero numeric user ID.
- `TESSERACT_CMD`: (Optional) Path to your Tesseract OCR binary (e.g., `C:\Program Files\Tesseract-OCR\tesseract.exe`).

### 3. Import Skills
In your Claude Code session, prompt:
> "Load all skills from the `skills/` directory."

---

## 🤖 Claude Code Triggers

| Action | Example Command |
| :--- | :--- |
| **Search** | "Search for high-IF papers on 'perovskite solar cells' using sci-search." |
| **Zotero Sync** | "Sync the last 10 items from my Zotero 'Materials' collection." |
| **Insight Extraction** | "Extract numerical core insights from `paper_test.pdf`." |
| **Figure Parsing** | "Extract Figure 3 from the PDF and split its subfigures." |
| **Refinement** | "Refine my abstract using the rebuttal-guide in sci-review." |

---

## 📁 Repository Structure

- `/skills`: Modular skills folders following oh-my-claudecode standards.
  - `/sci-figure`: Visual intelligence (from original Sh_Sci_Fig system).
  - `/sci-review`: Refinement references and response templates.
- `/scripts`: Core Python logic for search, extraction, and sync.
- `scripts/journal_db.json`: Decoupled journal metrics (Easy to update!).
- `requirements.txt`: Minimal dependencies for maximum portability.

---

## 🤝 Contributing
Contributions are welcome! Please add new journal metrics to `scripts/journal_db.json` or new writing templates to `sci-review/templates`.

## 📄 License
This project is licensed under the **MIT License**.

---
*Developed for autonomous agents and the scientific community.*
