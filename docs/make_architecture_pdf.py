"""Builds docs/architecture.pdf (and .svg): one-page architecture diagram showing
components, data flows and AI models. Run: python docs/make_architecture_pdf.py
Needs Google Chrome or Chromium on the PATH (or CHROME env var) to print the PDF.
"""
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent
W, H = 1400, 990

NAVY, INK, SLATE, MIST, LINE = "#0B2545", "#1C2733", "#5B6B7C", "#F4F6F9", "#C9D3DE"
GREEN, GREEN_BG, AMBER, AMBER_BG, PURPLE, RED = "#2E7D32", "#E3F2E6", "#B86A00", "#FDF0DC", "#6A1B9A", "#C62828"

parts = []


def rect(x, y, w, h, fill="#fff", stroke=LINE, sw=1.2, rx=8, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def text(x, y, lines, size=12, weight=400, color=INK, lh=None, anchor="start", italic=False):
    if isinstance(lines, str):
        lines = [lines]
    lh = lh or size * 1.3
    style = ' font-style="italic"' if italic else ""
    spans = "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else lh}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" '
                 f'text-anchor="{anchor}"{style}>{spans}</text>')


def rich(x, y, runs, size=12, lh=None):
    """runs: list of lines; each line a list of (text, weight, color)."""
    lh = lh or size * 1.3
    out = []
    for i, line in enumerate(runs):
        segs = "".join(f'<tspan font-weight="{w}" fill="{c}">{escape(t)}</tspan>' for t, w, c in line)
        out.append(f'<tspan x="{x}" dy="{0 if i == 0 else lh}">{segs}</tspan>')
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{INK}">{"".join(out)}</text>')


def arrow(x1, y1, x2, y2, color=SLATE, dash=None, sw=1.6, both=False, label=None, lx=None, ly=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    mid = color.strip("#")
    start = f' marker-start="url(#s{mid})"' if both else ""
    parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d} '
                 f'marker-end="url(#a{mid})"{start}/>')
    if label:
        text(lx if lx is not None else (x1 + x2) / 2 + 6, ly if ly is not None else (y1 + y2) / 2, label,
             size=10, color=color, italic=True)


def circle_num(cx, cy, n, r=13, fill=NAVY):
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>')
    text(cx, cy + 4.5, str(n), size=13, weight=700, color="#fff", anchor="middle")


def gate(cx, cy):
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{GREEN_BG}" stroke="{GREEN}" stroke-width="1.6"/>')
    parts.append(f'<path d="M{cx-4.5},{cy} l3,3.5 l6,-7" fill="none" stroke="{GREEN}" stroke-width="2"/>')


def heading(x, y, t):
    text(x, y, t.upper(), size=11, weight=700, color=SLATE)


# ---------------------------------------------------------------- title
text(28, 44, "Model Risk Factory – architecture", size=26, weight=700, color=NAVY)
text(28, 68, "Components, data flows and AI models  ·  EXL × Trinity Data & AI Hackathon 2026  ·  Challenge 04: Agentic model risk factory",
     size=12.5, color=SLATE)
# legend
lx = 930
arrow(lx, 40, lx + 34, 40, color=SLATE)
text(lx + 42, 44, "data flow (files)", size=10.5, color=SLATE)
arrow(lx + 150, 40, lx + 184, 40, color=AMBER, dash="5,4")
text(lx + 192, 44, "optional AI call", size=10.5, color=SLATE)
gate(lx + 300, 40)
text(lx + 316, 44, "human approval gate", size=10.5, color=SLATE)
text(lx, 66, "Runs locally: one Python environment, no cloud services, no database.", size=10.5, color=SLATE)

# ---------------------------------------------------------------- inputs column
heading(28, 102, "Inputs")
rect(20, 112, 235, 150, fill=MIST, stroke=MIST)
text(34, 136, "Public data", size=13.5, weight=700, color=NAVY)
text(34, 156, ["South German Credit (UCI 573,", "corrected 2019) · 1,000 loans · CC BY 4.0"], size=11)
text(34, 196, ["core/data.py: target 1 = bad risk,", "stratified 70/30 split, seed 42", "→ train.csv (700) · test.csv (300)"], size=11, color=SLATE)

rect(20, 278, 235, 252, fill=MIST, stroke=MIST)
text(34, 302, "Legacy model estate", size=13.5, weight=700, color=NAVY)
text(34, 320, "legacy_models/ (the bank's models)", size=11, color=SLATE)
estate = [("CR-PD-001", "R · glm logistic scorecard"), ("CR-EW-002", "Python · decision tree"),
          ("CR-PR-003", "Python · gradient boosting"), ("CR-BH-004", "SAS · PROC LOGISTIC")]
for i, (mid, desc) in enumerate(estate):
    y = 346 + i * 36
    text(34, y, mid, size=11.5, weight=700)
    text(34, y + 15, desc + (" (document only)" if mid == "CR-BH-004" else ""), size=11,
         color=PURPLE if mid == "CR-BH-004" else INK)
text(34, 494, ["artifacts/: R coefficients, scores, spec,", "R version and run time; .joblib models"], size=10.5, color=SLATE)

rect(20, 546, 235, 104, fill=MIST, stroke=MIST)
text(34, 570, "Simulated production batch", size=13.5, weight=700, color=NAVY)
text(34, 590, ["400 new applications from the hold-out", "data: 'stable' or 'drift' scenario", "(younger, larger loans, longer terms)"], size=11)

# ---------------------------------------------------------------- orchestration bar
heading(280, 102, "Agent pipeline")
rect(280, 112, 830, 44, fill=NAVY, stroke=NAVY)
rich(296, 139, [[("Orchestration  ", 700, "#fff"),
                 ("core/pipeline.py + core/state.py: a stage runs only after a named reviewer approves the previous one", 400, "#DDE6F0")]], size=11.5)
text(296, 152, "", size=2)
# second line inside the bar is too long; add a small caption under it instead
text(280, 172, "Re-running a stage resets every later approval · every run and decision is written to outputs/audit_log.jsonl",
     size=10.5, color=SLATE)

# ---------------------------------------------------------------- shared services row
sy, sh = 186, 108
rect(280, sy, 150, sh, fill="#fff", stroke=LINE)
text(292, sy + 22, "Configuration", size=12.5, weight=700, color=NAVY)
text(292, sy + 40, ["core/config.py · read", "by every agent: paths,", "thresholds (PSI 0.10/0.25,", "AUC 0.70, ratio 0.8, 1e-6)"], size=10.5)

rect(450, sy, 150, sh, fill=AMBER_BG, stroke=AMBER, dash="5,4")
text(462, sy + 22, "Claude API (optional)", size=12.5, weight=700, color=AMBER)
text(462, sy + 40, ["core/llm.py · prose only,", "temperature 0, cached,", "labelled ai_generated.", "No key → rule-based text"], size=10.5)

rect(620, sy, 490, sh, fill=GREEN_BG, stroke=GREEN)
text(634, sy + 22, "Deterministic maths – every number (no AI)", size=12.5, weight=700, color=GREEN)
rich(634, sy + 42, [
    [("metrics.py ", 700, INK), ("AUC, Gini, KS, Brier, Hosmer–Lemeshow, calibration, cost", 400, INK)],
    [("stability.py ", 700, INK), ("PSI on scores and inputs   ", 400, INK), ("parity.py ", 700, INK), ("coefficients + predictions", 400, INK)],
    [("fairness.py ", 700, INK), ("approval-rate ratio, equal-opportunity gap", 400, INK)],
    [("core/scoring.py ", 700, INK), ("loads redeveloped / .joblib models, scores new data", 400, INK)],
], size=10.5, lh=15)

# ---------------------------------------------------------------- agents row
ay, ah, aw = 330, 172, 150
agents = [
    ("Discover", ["Reads legacy_models/", "source without running it", "(regex + Python AST):", "method, inputs, owner,", "risk tier, doc age, SHA-256"], "inventory.json"),
    ("Document", ["Facts extracted from", "code + narrative (rules", "or Claude); each block", "labelled with its source;", "marked DRAFT"], "model_cards/*.md, .json"),
    ("Redevelop", ["Runs R (or recorded R", "outputs), generates", "Python, refits by IRLS,", "compares coefficients +", "1,000 predictions ≤ 1e-6"], "parity.json + Python"),
    ("Validate", ["Hold-out performance,", "stability, fairness;", "rule-based findings and", "RAG rating; HTML report", "per model"], "validation .json/.html"),
    ("Monitor", ["Scores the new batch;", "input + score PSI, AUC", "and approval-rate change;", "alerts trigger", "re-validation"], "monitoring/latest.json"),
]
xs = [280, 450, 620, 790, 960]
for i, ((name, body, out), x) in enumerate(zip(agents, xs)):
    rect(x, ay, aw, ah, fill="#fff", stroke=NAVY, sw=1.4)
    circle_num(x + 22, ay + 22, i + 1)
    text(x + 42, ay + 27, name, size=14, weight=700, color=NAVY)
    text(x + 12, ay + 54, body, size=10.5, lh=14.5)
    parts.append(f'<line x1="{x+10}" y1="{ay+130}" x2="{x+aw-10}" y2="{ay+130}" stroke="{LINE}" stroke-width="1"/>')
    text(x + 12, ay + 148, "writes", size=9.5, color=SLATE)
    text(x + 12, ay + 162, out, size=10.5, weight=700, color=INK)
    if i < 4:
        arrow(x + aw, ay + 70, x + aw + 20, ay + 70, color=SLATE, sw=1.4)
        gate(x + aw + 10, ay + 100)
gate(1110 - 10, ay + ah + 18)
text(1086, ay + ah + 22, "final sign-off", size=10, color=GREEN, anchor="end")
text(280, ay + ah + 22, "Each ✓ = Approve / Reject by a named reviewer in the dashboard or CLI", size=10, color=GREEN)

# inputs → agents
arrow(255, 400, 280, 400, color=SLATE)                         # estate → discover
arrow(137, 262, 137, 278, color=SLATE)
text(146, 274, "trains", size=9.5, color=SLATE, italic=True)
text(258, 178, "", size=2)
parts.append(f'<path d="M255,600 L990,600 L990,{ay+ah}" fill="none" stroke="{SLATE}" stroke-width="1.6" marker-end="url(#a{SLATE.strip("#")})"/>')
text(600, 594, "new batch → Monitor", size=10, color=SLATE, italic=True)

# agents → services
arrow(525, ay, 525, sy + sh, color=AMBER, dash="5,4")          # document → claude
arrow(695, ay, 695, sy + sh, color=GREEN)                       # redevelop → maths
arrow(865, ay, 865, sy + sh, color=GREEN)                       # validate → maths
arrow(1035, ay, 1035, sy + sh, color=GREEN)                     # monitor → maths
parts.append(f'<path d="M845,{ay} C845,{ay-20} 600,{ay-14} 590,{sy+sh+2}" fill="none" stroke="{AMBER}" stroke-width="1.4" stroke-dasharray="5,4" marker-end="url(#a{AMBER.strip("#")})"/>')
text(702, ay - 8, "report commentary", size=9.5, color=AMBER, italic=True)

# ---------------------------------------------------------------- outputs store
oy = 626
rect(280, oy, 830, 54, fill=MIST, stroke=LINE)
rich(296, oy + 22, [[("outputs/  ", 700, NAVY), ("file-based hand-offs between agents (JSON): ", 400, SLATE),
                     ("inventory.json · model_cards/ · reports/ (parity, validation, ", 400, INK)],
                    [("portfolio estate health .json/.html) · monitoring/ · pipeline_state.json · audit_log.jsonl", 400, INK)]],
     size=11, lh=16)
for x in xs:
    arrow(x + 75, ay + ah + 32, x + 75, oy, color=SLATE, sw=1.3)

# ---------------------------------------------------------------- interfaces column
heading(1140, 102, "Interfaces and people")
rect(1140, 112, 240, 236, fill="#fff", stroke=NAVY, sw=1.4)
text(1154, 136, "Streamlit dashboard", size=13.5, weight=700, color=NAVY)
text(1154, 154, "app.py · localhost:8501", size=10.5, color=SLATE)
text(1154, 176, ["Overview · Estate health", "Model inventory · Documentation", "Redevelopment · Validation", "Monitoring · Approvals & audit trail"], size=11, lh=15)
text(1154, 246, ["Run / Approve / Reject buttons call", "core/pipeline.py; every number", "shown is read from outputs/,", "never hard-coded"], size=10.5, color=SLATE, lh=14)

rect(1140, 362, 240, 64, fill="#fff", stroke=LINE)
text(1154, 386, "Command line", size=13, weight=700, color=NAVY)
text(1154, 404, "main.py: setup · run · approve · reject ·", size=10.5)
text(1154, 418, "status · portfolio · run-all · reset", size=10.5)

rect(1140, 440, 240, 210, fill=MIST, stroke=MIST)
text(1154, 464, "People", size=13.5, weight=700, color=NAVY)
people = [("Model validator", "runs stages, reviews, approves"), ("Model risk manager", "estate health: what is failing, why"),
          ("Model owner", "signs off draft model cards"), ("Auditor", "audit log, file hashes, R run info")]
for i, (r_, d) in enumerate(people):
    text(1154, 490 + i * 39, r_, size=11.5, weight=700)
    text(1154, 505 + i * 39, d, size=10.5, color=SLATE)

arrow(1110, 134, 1140, 134, color=SLATE, both=True)            # orchestration <-> dashboard
arrow(1110, 395, 1140, 395, color=SLATE, both=True)            # pipeline <-> CLI
parts.append(f'<path d="M1110,653 L1125,653 L1125,300 L1140,300" fill="none" stroke="{SLATE}" stroke-width="1.6" marker-end="url(#a{SLATE.strip("#")})"/>')
text(1118, 645, "reads", size=9.5, color=SLATE, italic=True, anchor="end")

# ---------------------------------------------------------------- AI & models panel
py = 706
heading(28, py, "AI and models")
rect(20, py + 10, 1360, 252, fill="#fff", stroke=LINE)
# col 1: governed models
text(36, py + 36, "Governed models (the bank's estate)", size=13, weight=700, color=NAVY)
rows = [("CR-PD-001", "Logistic regression, R glm (binomial/logit)", "Rebuilt in Python; parity ~1e-15"),
        ("CR-EW-002", "Decision tree (CART), scikit-learn", "Validated: mis-calibrated"),
        ("CR-PR-003", "Gradient boosting, scikit-learn", "Validated: overfitting"),
        ("CR-BH-004", "Logistic regression, SAS (stepwise)", "Documented only: BLOCKED")]
for i, (m, d, s) in enumerate(rows):
    y = py + 62 + i * 44
    text(36, y, m, size=11.5, weight=700)
    text(120, y, d, size=11)
    text(120, y + 16, s, size=10.5, color=PURPLE if "BLOCKED" in s else SLATE)
text(36, py + 244, "All trained on the 700-row training split; evaluated on the 300-row hold-out.", size=10, color=SLATE, italic=True)

parts.append(f'<line x1="470" y1="{py+24}" x2="470" y2="{py+248}" stroke="{LINE}"/>')
# col 2: statistical methods
text(488, py + 36, "Statistical methods used by the factory", size=13, weight=700, color=GREEN)
meth = [("Migration", "IRLS / Newton–Raphson logistic refit (same estimator as R glm)"),
        ("Discrimination", "ROC AUC, Gini = 2·AUC − 1, Kolmogorov–Smirnov"),
        ("Calibration", "decile table, Hosmer–Lemeshow test, Brier score"),
        ("Stability", "Population Stability Index (WARN ≥ 0.10, ALERT ≥ 0.25)"),
        ("Fairness", "approval-rate ratio (screen 0.8), equal-opportunity gap"),
        ("Decision / cost", "approve if PD < 1/6, from the 5:1 cost matrix")]
for i, (k, v) in enumerate(meth):
    y = py + 62 + i * 30
    text(488, y, k, size=11.5, weight=700)
    text(600, y, v, size=11)
text(488, py + 244, "numpy · pandas · scipy · scikit-learn · unit-tested against known answers (pytest)", size=10, color=SLATE, italic=True)

parts.append(f'<line x1="975" y1="{py+24}" x2="975" y2="{py+248}" stroke="{LINE}"/>')
# col 3: generative AI
text(993, py + 36, "Generative AI (optional)", size=13, weight=700, color=AMBER)
gen = ["Claude (Anthropic) via API; model set by", "CLAUDE_MODEL, default claude-sonnet-5-5",
       "Writes model-card narrative and report", "commentary only, from facts already computed",
       "Never computes or edits a metric; output", "labelled ai_generated and cached on disk",
       "Prompts contain code and aggregate results,", "never personal data"]
text(993, py + 62, gen, size=11, lh=15.5)
text(993, py + 196, "Without an API key the pipeline runs fully,", size=11, weight=700)
text(993, py + 212, "with rule-based text in place of Claude.", size=11, weight=700)
text(993, py + 244, "Development: Claude used as a coding assistant (declared).", size=10, color=SLATE, italic=True)

# ---------------------------------------------------------------- assemble
markers = ""
for col in {SLATE, GREEN, AMBER, NAVY}:
    c = col.strip("#")
    markers += (f'<marker id="a{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>'
                f'<marker id="s{c}" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                f'<path d="M10,0 L0,5 L10,10 z" fill="{col}"/></marker>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Helvetica, Arial, sans-serif"><defs>{markers}</defs>'
       f'<rect width="{W}" height="{H}" fill="#fff"/>{"".join(parts)}</svg>')
(OUT / "architecture.svg").write_text(svg)
html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>@page{size:297mm 210mm;margin:0}'
        'html,body{margin:0;padding:0}svg{width:297mm;height:210mm;display:block}</style></head><body>'
        + svg + '</body></html>')
html_file = OUT / "architecture_print.html"
html_file.write_text(html)

chrome = os.environ.get("CHROME") or next((shutil.which(c) for c in
          ["google-chrome", "chromium", "chromium-browser", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
          if shutil.which(c) or os.path.exists(c)), None)
if chrome:
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT / 'architecture.pdf'}", html_file.as_uri()],
                   check=True, capture_output=True)
    html_file.unlink()
    print(f"Saved {OUT / 'architecture.pdf'} and architecture.svg")
else:
    print(f"Chrome not found: open {html_file} in a browser and print to PDF (A4 landscape). SVG saved.")
