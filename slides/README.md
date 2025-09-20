Slide deck for the KG-CAE / MatterWave project

This directory contains a lightweight slide deck skeleton suitable for quick edits and export to Reveal.js or PowerPoint (via Pandoc). Files:

- `Deck.md` — main slide content in Markdown, structured for Reveal.js or Pandoc conversion.
- `notes.md` — speaker notes and slide-by-slide talking points.

How to use (Windows / PowerShell):

- Present locally with reveal-md (Node):

  1. npm install -g reveal-md
  2. reveal-md .\Deck.md --css custom.css

- Export to PowerPoint using Pandoc (requires Pandoc installed):

  pandoc .\Deck.md -t pptx -o .\Deck.pptx

Design decisions:
- Keep slides concise and focused on the research narrative. The Executive Summary in `Deck.md` is intentionally non-TL;DR and provides the audience with a clear, research-oriented framing.

Links:
- Theoretical framing & expected behaviors: `..\Theoretical_Framing_and_Expected_Behaviors.md`
- Publication plan and prioritized experiments: `..\RESEARCH_PUBLICATION_PLAN.md`

Next steps:
- I can add SVG exports of the Mermaid diagrams in `DataGenerationPipeline_Detailed.md` and create a `figures/` folder if you'd like. I can also generate an export-ready `Deck.pptx` for distribution.

Python exporter (fallback when Pandoc is not installed):

1. Create a virtual environment (PowerShell):

  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

2. Install requirements:

  pip install -r requirements.txt

3. Run the exporter:

  python export_to_pptx.py .\Deck.md .\Deck.pptx

This will produce `Deck.pptx` in the `slides` folder. The exporter is intentionally minimal and targets readability and quick edits.

Note: I attempted to run the exporter in this environment but installing Python packages is not allowed here. To generate `Deck.pptx`, run the three steps above on your local machine (PowerShell) after cloning the repo.

Suggested local PowerShell commands (copy/paste):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python export_to_pptx.py .\Deck.md .\Deck.pptx
```

After running the commands above `Deck.pptx` will be available in the `slides` folder for editing or sharing.

Convert PPTX → PDF (PowerPoint required)

If you have Microsoft PowerPoint on Windows, use the included PowerShell helper to convert the generated `Deck.pptx` to `Deck.pdf`:

```powershell
.\pptx_to_pdf.ps1 -InputPath .\slides\Deck.pptx -OutputPath .\slides\Deck.pdf
```

LibreOffice alternative (cross-platform, headless):

```powershell
soffice --headless --convert-to pdf --outdir .\slides .\slides\Deck.pptx
```

Note: The PowerShell helper uses COM automation and requires PowerPoint installed. The LibreOffice command requires `soffice` in PATH.

Automated generation (timestamped outputs)

Use the included wrapper to create a timestamped PPTX and PDF in the project `reports/` folder:

```powershell
python .\slides\generate_presentation.py
```

What it does:
- Produces `reports/Deck_YYYYMMDD_HHMMSS.pptx` and attempts to create `reports/Deck_YYYYMMDD_HHMMSS.pdf`.
- Tries PowerPoint COM export via `pywin32` first; falls back to LibreOffice (`soffice`) if missing.

Requirements for full functionality:
- `python-pptx` (for the PPTX exporter), and optionally `pywin32` for COM export.
- Or LibreOffice (`soffice`) available in PATH for headless PDF conversion.
