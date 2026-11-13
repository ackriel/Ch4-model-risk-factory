# CLAUDE.md - rules for AI coding assistants working on this repo

## Project
Model Risk Factory: 5-stage pipeline (discover → document → redevelop → validate → monitor) with human approval gates. EXL × Trinity hackathon, Challenge 04. See README.md.

## Non-negotiable rules
1. **AI never calculates metrics.** All numbers come from `validation/*.py` (numpy/pandas/scipy/sklearn). LLM text may only quote numbers passed into the prompt.
2. **Label every text block's source:** `extracted`, `rule_based` or `ai_generated (<model>)`.
3. **The pipeline must run without an API key.** `core/llm.py` returns None → fall back to templates.
4. **Never weaken the approval gates** in `core/state.py`. Re-running a stage invalidates later stages.
5. **Never claim regulatory compliance.** Reports say they *support* human validation.
6. **Public data only.** No personal data. Target `default_flag`: 1 = bad risk.
7. **Don't regenerate `data/train.csv` / `test.csv`.** The recorded R outputs depend on this exact split.

## Conventions
- Python 3.11+, run everything from the repo root. Paths come from `core/config.py`; thresholds live there too.
- Agents expose `run(**kwargs) -> dict` (a short summary) and write full results to `outputs/` as JSON.
- Agents communicate only through files in `outputs/` (JSON), never through in-memory state.
- Model IDs follow `CR-XX-NNN`. Legacy files start with a header block (`# MODEL_ID: ...`) that the Discover agent parses.
- Tests: `pytest -q` must pass before committing. Add a test for any new metric, with a known answer.

## Commands
`python main.py setup` · `python main.py run <stage>` · `python main.py approve <stage> --reviewer X` · `streamlit run app.py` · `pytest -q`

## Team ownership (edit only your folders; read anything)
- Software engineer: `agents/`, `core/`, `app.py`, `main.py`, `CLAUDE.md`, `README.md`
- Chemical engineer: `legacy_models/`, `validation/`, `tests/`
- Industrial engineer: `docs/`, `templates/`
