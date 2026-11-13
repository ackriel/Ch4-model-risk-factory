"""Draws docs/architecture.png (one-page architecture diagram). Run: python docs/make_architecture_diagram.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

NAVY, BLUE, GREEN, AMBER, GREY = "#0b2545", "#1f6fb2", "#2e7d32", "#ef8f00", "#5b6b7c"

fig, ax = plt.subplots(figsize=(16, 9.6))
ax.set_xlim(0, 16); ax.set_ylim(0, 9.6); ax.axis("off")


def box(x, y, w, h, title, body="", color=BLUE, fill="#ffffff", fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                linewidth=1.6, edgecolor=color, facecolor=fill))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=fs + 1, weight="bold", color=color)
    if body:
        ax.text(x + w / 2, y + h - 0.55, body, ha="center", va="top", fontsize=fs - 1.2, color="#1c2733", linespacing=1.35)


def arrow(x1, y1, x2, y2, color=GREY, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                                 color=color, lw=1.5, linestyle=ls))


ax.text(8, 9.35, "Model Risk Factory - architecture", ha="center", fontsize=17, weight="bold", color=NAVY)
ax.text(8, 9.0, "Local Python prototype · one environment · CSV in, JSON between agents, HTML reports out",
        ha="center", fontsize=10.5, color=GREY)

# Inputs
box(0.2, 5.2, 2.6, 3.4, "Inputs",
    "South German Credit data\n(UCI, corrected 2019)\n1,000 loans · CSV\n\nLegacy model estate\n• R  glm scorecard\n• Python decision tree\n• Python gradient boosting\n• SAS (document only)",
    color=GREY, fill="#f4f6f9")

# Agents
stages = [("1  Discover", "Static code scan\n(regex + AST)\n→ inventory.json"),
          ("2  Document", "Facts extracted +\nnarrative (rules or\nClaude) → model cards"),
          ("3  Redevelop", "Generates Python from\nR spec, refits (IRLS),\nparity ≤ 1e-6"),
          ("4  Validate", "Performance, stability,\nfairness, findings, RAG\n→ HTML report"),
          ("5  Monitor", "Simulated new batch,\nPSI drift, AUC change\n→ alerts")]
xs = [3.3, 5.85, 8.4, 10.95, 13.5]
for (t, b), x in zip(stages, xs):
    box(x, 6.55, 2.3, 1.55, t, b, color=BLUE)
for x in xs[:-1]:
    arrow(x + 2.3, 7.3, x + 2.55, 7.3, color=BLUE)
arrow(2.8, 7.3, 3.3, 7.3)

# Human gates
for x in xs:
    ax.add_patch(FancyBboxPatch((x + 0.3, 5.85), 1.7, 0.45, boxstyle="round,pad=0.02,rounding_size=0.1",
                                facecolor="#e3f2e6", edgecolor=GREEN, lw=1.3))
    ax.text(x + 1.15, 6.075, "Human approve / reject", ha="center", va="center", fontsize=7.8, color=GREEN, weight="bold")
    arrow(x + 1.15, 6.55, x + 1.15, 6.3, color=GREEN)
ax.text(9.6, 5.5, "A stage only runs after the previous stage is approved · re-running a stage resets later approvals",
        ha="center", fontsize=9.5, color=GREEN, style="italic")

# Deterministic maths + optional AI
box(3.3, 2.55, 6.2, 2.0, "Deterministic maths (validation/*.py) - all numbers",
    "metrics.py: AUC, Gini, KS, Brier, Hosmer-Lemeshow, calibration, cost matrix\n"
    "stability.py: PSI (scores & inputs)   fairness.py: approval-rate ratio, equal opportunity\n"
    "parity.py: coefficient & prediction differences vs tolerance\n"
    "numpy · pandas · scipy · scikit-learn", color=GREEN, fill="#f3faf4", fs=9.2)
box(9.9, 2.55, 5.9, 2.0, "Optional Claude API (core/llm.py) - text only",
    "Writes model-card prose and report commentary from facts\nalready computed. Temperature 0, cached to disk.\n"
    "Never computes metrics. Every text block labelled with its source.\nNo API key → rule-based templates (pipeline still runs).",
    color=AMBER, fill="#fff8ee", fs=9.2)
arrow(6.4, 5.25, 6.4, 4.6, color=GREEN)
ax.text(6.55, 4.9, "agents call for every number", fontsize=8.5, color=GREEN, va="center")
arrow(12.85, 5.25, 12.85, 4.6, color=AMBER)
ax.text(13.0, 4.9, "agents call for prose only", fontsize=8.5, color=AMBER, va="center")

# Outputs + UI
box(0.2, 0.35, 7.4, 1.6, "Outputs (outputs/)",
    "inventory.json · model_cards/ (.md + .json) · reports/*_parity.json · reports/*_validation_report.html\n"
    "monitoring/latest.json (alerts) · pipeline_state.json · audit_log.jsonl (every run & decision)",
    color=NAVY, fill="#f4f6f9")
box(8.0, 0.35, 7.8, 1.6, "Interfaces",
    "Streamlit dashboard (app.py): overview, inventory, documentation, redevelopment,\n"
    "validation, monitoring, approvals & audit trail - buttons call the real pipeline\n"
    "CLI (main.py): setup · run · approve · reject · status · run-all",
    color=NAVY, fill="#f4f6f9")
arrow(6.4, 2.55, 6.4, 1.95, color=NAVY)
arrow(7.6, 1.15, 8.0, 1.15, color=NAVY, style="<|-|>")

out = Path(__file__).resolve().parent / "architecture.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved {out}")
