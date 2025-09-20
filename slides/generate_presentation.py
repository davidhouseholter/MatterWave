#!/usr/bin/env python3
"""
Generate a timestamped PPTX from Deck.md and convert it to PDF, placing
outputs in the repository's `reports/` folder.

Behavior:
- Creates `reports/` if missing.
- Uses the existing exporter `export_to_pptx.py` to write a PPTX (timestamped).
- Tries PowerPoint COM automation (via pywin32) to export PDF on Windows.
- Falls back to LibreOffice (`soffice`) headless conversion if COM is unavailable.

Usage:
  python generate_presentation.py

Requirements (optional paths):
- python-pptx (for the PPTX exporter) — required by export_to_pptx.py
- pywin32 (win32com) if you want COM-based PDF export on Windows
- LibreOffice (`soffice`) as an alternate PDF converter

The script will print the produced file paths on success.
"""
from pathlib import Path
from datetime import datetime
import sys
import subprocess


def main():
    repo_root = Path(__file__).resolve().parents[1]
    slides_dir = Path(__file__).resolve().parent
    deck_md = slides_dir / 'Deck.md'
    if not deck_md.exists():
        print('Deck.md not found in slides/; aborting')
        return 2

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    reports_dir = repo_root / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    pptx_name = f'Deck_{timestamp}.pptx'
    pdf_name = f'Deck_{timestamp}.pdf'
    pptx_path = reports_dir / pptx_name
    pdf_path = reports_dir / pdf_name

    # Import the local exporter (slides/export_to_pptx.py)
    sys.path.insert(0, str(slides_dir))
    try:
        import export_to_pptx
    except Exception as e:
        print('Failed to import export_to_pptx.py (install python-pptx?):', e)
        return 3

    try:
        export_to_pptx.make_pptx(deck_md, pptx_path)
        print('Wrote PPTX:', pptx_path)
    except Exception as e:
        print('Failed to create PPTX:', e)
        return 4

    # Try PowerPoint COM automation (Windows + pywin32)
    try:
        import win32com.client
        print('Attempting PDF export via PowerPoint COM...')
        pp = win32com.client.Dispatch('PowerPoint.Application')
        pp.Visible = 1
        pres = pp.Presentations.Open(str(pptx_path), False, False, False)
        pres.SaveAs(str(pdf_path), 32)  # 32 = PDF
        pres.Close()
        pp.Quit()
        print('Wrote PDF via PowerPoint:', pdf_path)
        return 0
    except Exception as e:
        print('PowerPoint COM export unavailable or failed:', e)

    # Fallback: try LibreOffice headless conversion
    try:
        print('Attempting PDF export via LibreOffice (soffice)...')
        subprocess.run([
            'soffice', '--headless', '--convert-to', 'pdf',
            '--outdir', str(reports_dir), str(pptx_path)
        ], check=True)
        # LibreOffice will write a PDF with same base name into reports_dir
        expected = reports_dir / pptx_path.with_suffix('.pdf').name
        if expected.exists():
            expected.rename(pdf_path)
            print('Wrote PDF via LibreOffice:', pdf_path)
            return 0
        else:
            print('LibreOffice conversion ran but expected PDF not found:', expected)
            return 6
    except Exception as e:
        print('LibreOffice conversion failed or soffice not found:', e)
        return 5


if __name__ == '__main__':
    raise SystemExit(main())
