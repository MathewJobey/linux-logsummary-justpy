# linux-logsummary-justpy
A JustPy-based pipeline for parsing, analyzing, and summarizing Linux system security logs (Work In Progress)
## Current Status

- Upload a Linux log file through a JustPy UI.
- Clean the log with a configurable blacklist (including scan-and-add suggestions).
- Parse the cleaned log into templates and produce an Excel analysis.
- Generate natural-language meanings for templates (cached to avoid regenerating).
- Step-by-step UI flow: Clean → Parse → Meaning generation (with status and toggles).

## Getting Started

1) Install dependencies:
```bash
pip install -r requirements.txt
```

2) Run the app:
```bash
python pipeline.py
```

3) Open the app in your browser (default port `8000`), upload a log, and follow the steps.

## Notes

- Model weights and cache are stored locally (`models/`, `cache/`).
- Meaning generation uses Phi-3; CPU is supported but slow—GPU recommended.
- Outputs are saved alongside the uploaded log (cleaned log, parsed Excel, meaning Excel).
- Accordion UI shows blacklist entries; scanning finds new process names to add.
- Template summaries are viewable in a collapsible table after parsing.