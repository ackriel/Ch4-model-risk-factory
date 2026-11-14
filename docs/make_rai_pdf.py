"""Builds docs/responsible_ai_note.pdf (one A4 page) from docs/responsible_ai_note.md.
Run: python docs/make_rai_pdf.py   (needs `pip install markdown` and Google Chrome / Chromium)
"""
import os
import shutil
import subprocess
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
md = (DOCS / "responsible_ai_note.md").read_text()
title, body = md.split("\n", 1)
body_html = markdown.markdown(body, extensions=["tables"])

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 11mm 14mm 9mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #1C2733; font-size: 9.2pt; line-height: 1.3; margin: 0; }}
header {{ background: #0B2545; color: #fff; padding: 8px 14px; border-radius: 6px; margin-bottom: 8px; }}
header h1 {{ margin: 0; font-size: 15pt; }}
header p {{ margin: 3px 0 0; font-size: 8.8pt; color: #C9D6E6; }}
p {{ margin: 0 0 5px; }}
strong {{ color: #0B2545; }}
table {{ border-collapse: collapse; width: 100%; margin: 4px 0 8px; font-size: 8.8pt; }}
th, td {{ border: 1px solid #D5DCE4; padding: 2.5px 6px; text-align: left; vertical-align: top; }}
th {{ background: #F4F6F9; }}
ul {{ margin: 1px 0 5px; padding-left: 16px; }} li {{ margin-bottom: 1.5px; }}
code {{ font-size: 8.6pt; background: #F4F6F9; padding: 0 3px; border-radius: 3px; }}
footer {{ margin-top: 8px; font-size: 8pt; color: #5B6B7C; border-top: 1px solid #D5DCE4; padding-top: 5px; }}
</style></head><body>
<header><h1>{title.lstrip('# ').strip()}</h1>
<p>EXL × Trinity Data &amp; AI Hackathon 2026 · Challenge 04 · github.com/ackriel/Ch4-model-risk-factory</p></header>
{body_html}
<footer>Public data only · no personal data · every metric computed by deterministic, unit-tested code · AI-written text labelled and human-reviewed.</footer>
</body></html>"""
src = DOCS / "rai_print.html"
src.write_text(html)
chrome = os.environ.get("CHROME") or next((c for c in ["google-chrome", "chromium", "chromium-browser",
          "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if shutil.which(c) or os.path.exists(c)), None)
if not chrome:
    raise SystemExit(f"Chrome not found: open {src} in a browser and print to PDF (A4).")
subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={DOCS / 'responsible_ai_note.pdf'}", src.as_uri()], check=True, capture_output=True)
src.unlink()
print(f"Saved {DOCS / 'responsible_ai_note.pdf'}")
