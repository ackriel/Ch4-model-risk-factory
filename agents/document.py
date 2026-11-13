"""Stage 2 - Document agent.

For every model in the inventory, writes a model card (JSON + Markdown) to
outputs/model_cards/. Each section records where its text came from:

  * "extracted"     - read directly from the source code / inventory (deterministic)
  * "rule_based"    - generated from explicit rules in this file (deterministic)
  * "ai_generated"  - written by Claude from the extracted facts (optional)

Every card is marked "DRAFT - requires human review".
"""
from __future__ import annotations

import json
import re

from agents import discover
from core import config, llm, state

PROTECTED_OR_PROXY = {
    "age": "age (protected characteristic under the Equality Act 2010)",
    "personal_status_sex": "personal status and sex (sex is a protected characteristic)",
    "foreign_worker": "foreign-worker status (potential proxy for nationality / race)",
}


def extract_hyperparameters(text: str, language: str) -> dict:
    params = {}
    if language == "Python":
        for name, val in re.findall(r"(\w+)=([\w.\"']+)", text):
            if name in {"max_depth", "min_samples_leaf", "n_estimators", "learning_rate",
                        "subsample", "class_weight", "random_state"}:
                params[name] = val.strip("\"'")
    elif language == "R":
        fam = re.search(r"family\s*=\s*(\w+\([^)]*\))", text)
        if fam:
            params["family"] = fam.group(1)
    elif language == "SAS":
        sel = re.search(r"selection\s*=\s*(\w+)", text, flags=re.I)
        if sel:
            params["variable_selection"] = sel.group(1)
        for k in ("slentry", "slstay"):
            m = re.search(rf"{k}\s*=\s*([\d.]+)", text, flags=re.I)
            if m:
                params[k] = m.group(1)
    return params


def extract_data_source(text: str, language: str) -> str:
    if language == "R":
        return ", ".join(re.findall(r'read\.csv\("([^"]+)"', text)) or "not detected"
    if language == "Python":
        return "data/train.csv and data/test.csv via core.data.load_split()" if "load_split" in text else "not detected"
    if language == "SAS":
        sets = re.findall(r"set\s+([\w.]+)\s*;", text, flags=re.I)
        return ", ".join(sets) + " (production SAS library, not available)" if sets else "not detected"
    return "not detected"


def rule_based_sections(m: dict, params: dict) -> dict:
    method = m["methodology"].lower()
    feats = set(m["input_features"])
    protected = [PROTECTED_OR_PROXY[f] for f in PROTECTED_OR_PROXY if f in feats]

    if "logistic" in method:
        methodology = ("Binary logistic regression estimating the probability of default (PD) "
                       "as a logit-linear function of the inputs. Categorical inputs enter as "
                       "dummy variables against a reference level.")
        assumptions = [
            "Log-odds of default are linear in each numeric input (no transformation or binning detected).",
            "Observations are independent; no account-level or time clustering is modelled.",
            "Effects are additive: no interaction terms are specified.",
            "The development sample is representative of the population scored today.",
        ]
        limitations = ["Cannot capture non-linear effects or interactions unless explicitly engineered."]
    elif "tree" in method:
        methodology = ("Single classification tree (CART) that splits applicants into a small "
                       "number of leaves; the PD is the (re-weighted) default share in the leaf.")
        assumptions = ["Risk is constant within each leaf.",
                       "The tree structure found on the development sample is stable."]
        limitations = ["Produces a handful of distinct scores, so ranking within a leaf is impossible.",
                       "Class weighting ('balanced') inflates PDs: scores are rankings, not calibrated probabilities."]
    elif "boosting" in method:
        methodology = ("Gradient-boosted ensemble of shallow decision trees; each tree corrects the "
                       "errors of the previous ones. Output is a PD estimate.")
        assumptions = ["Development sample is representative.",
                       "Hyperparameters chosen on the development data generalise."]
        limitations = ["Low intrinsic interpretability: individual decisions need explanation tools (e.g. SHAP).",
                       "Higher risk of overfitting on a small sample (700 training rows)."]
    else:
        methodology = "Methodology could not be identified automatically."
        assumptions, limitations = [], []

    limitations.append("Developed on 1,000 historical German loans from 1973-1975: a small, old, "
                       "non-UK sample used here as a stand-in for bank data.")
    risks = []
    if protected:
        risks.append("Uses " + "; ".join(protected) + " as a direct input. Requires a documented "
                     "justification and fairness testing before use in customer decisions.")
    if m.get("documentation_stale"):
        risks.append(f"Documentation last reviewed {(m.get('last_documentation_review') or '')[:7]} "
                     f"({m.get('documentation_age_years')} years ago): out of date.")
    if params.get("variable_selection", "").lower() == "stepwise":
        risks.append("Stepwise variable selection is unstable and inflates apparent significance.")
    if m["language"] == "SAS":
        risks.append("Depends on a SAS licence and a production library not available for "
                     "independent re-execution: the model cannot be validated as-is.")
    if not m.get("executable"):
        risks.append("Model could not be executed in the factory, so no performance evidence exists.")
    if "tree" in method:
        risks.append("Coarse scores may produce cliff-edge decisions for similar customers.")
    if "boosting" in method:
        risks.append("Explainability risk: adverse-action reasons are hard to give to declined customers.")

    purpose = m.get("purpose") or "Not stated in source code."
    if m.get("business_use"):
        purpose = purpose.rstrip(".") + f". Business use: {m['business_use']}."
    return {"purpose": purpose, "methodology": methodology, "assumptions": assumptions,
            "limitations": limitations, "risks": risks}


def ai_sections(m: dict, params: dict, base: dict, source_code: str) -> dict | None:
    prompt = (
        "Write the narrative sections of a model card for the model below. Return ONLY JSON "
        'with keys "purpose" (string), "methodology" (string), "assumptions" (list of strings), '
        '"limitations" (list of strings), "risks" (list of strings). Max 5 items per list, one '
        "sentence each. Base everything on the facts and code given.\n\n"
        f"FACTS:\n{json.dumps({k: m[k] for k in ['model_id','model_name','purpose','business_use','language','methodology','target_variable','input_features','last_documentation_review','executable']}, indent=1)}\n"
        f"HYPERPARAMETERS: {json.dumps(params)}\n"
        f"RULE-BASED DRAFT (improve, do not contradict):\n{json.dumps(base, indent=1)}\n\n"
        f"SOURCE CODE:\n```\n{source_code[:6000]}\n```"
    )
    res = llm.generate(prompt, max_tokens=1200)
    if res is None:
        return None
    try:
        text = res["text"]
        parsed = json.loads(text[text.index("{"): text.rindex("}") + 1])
        parsed["_model"] = res["model"]
        return parsed
    except (ValueError, KeyError):
        return None


def build_card(m: dict) -> dict:
    source_code = (config.ROOT / m["source_file"]).read_text(errors="replace")
    params = extract_hyperparameters(source_code, m["language"])
    base = rule_based_sections(m, params)
    ai = ai_sections(m, params, base, source_code)
    narrative_source = f"ai_generated ({ai.pop('_model')})" if ai else "rule_based"
    sections = ai or base
    return {
        "model_id": m["model_id"],
        "model_name": m["model_name"],
        "status": "DRAFT - requires human review",
        "generated_at": state.now(),
        "facts": {
            "source": "extracted",
            "owner": m["owner"],
            "language": m["language"],
            "methodology_detected": m["methodology"],
            "target_variable": m["target_variable"],
            "target_definition": "1 = bad risk (credit contract not complied with), 0 = good risk",
            "input_variables": [
                {"name": f, "type": "numeric" if f in config.NUMERIC_FEATURES else "categorical",
                 "protected_or_proxy": f in PROTECTED_OR_PROXY}
                for f in m["input_features"]],
            "hyperparameters": params,
            "data_source": extract_data_source(source_code, m["language"]),
            "source_file": m["source_file"],
            "source_sha256": m["sha256"],
            "risk_tier": m["risk_tier"],
            "executable_in_factory": m["executable"],
        },
        "narrative": {"source": narrative_source, **{k: sections.get(k) for k in
                      ["purpose", "methodology", "assumptions", "limitations", "risks"]}},
    }


def to_markdown(card: dict) -> str:
    f, n = card["facts"], card["narrative"]
    lines = [f"# Model card: {card['model_name']} ({card['model_id']})", "",
             f"> **{card['status']}** - generated {card['generated_at']} by the Document agent.", "",
             "## Facts (extracted from source code)", "",
             "| Field | Value |", "|---|---|"]
    for k in ["owner", "language", "methodology_detected", "target_variable", "target_definition",
              "data_source", "risk_tier", "executable_in_factory", "source_file"]:
        lines.append(f"| {k.replace('_', ' ').capitalize()} | {f[k]} |")
    lines += ["", "### Input variables", "", "| Variable | Type | Protected / proxy |", "|---|---|---|"]
    for v in f["input_variables"]:
        lines.append(f"| {v['name']} | {v['type']} | {'YES' if v['protected_or_proxy'] else ''} |")
    if f["hyperparameters"]:
        lines += ["", "### Settings found in code", ""]
        lines += [f"- `{k}` = {v}" for k, v in f["hyperparameters"].items()]
    lines += ["", f"## Narrative (source: {n['source']})", "",
              "### Purpose", "", str(n["purpose"]), "", "### Methodology", "", str(n["methodology"])]
    for sec in ["assumptions", "limitations", "risks"]:
        lines += ["", f"### {sec.capitalize()}", ""] + [f"- {x}" for x in (n[sec] or [])]
    lines += ["", "---", "_Facts are extracted deterministically. Narrative text must be checked by "
              "a model owner before this card is relied on. Producing this card does not by itself "
              "demonstrate compliance with PRA SS1/23._"]
    return "\n".join(lines) + "\n"


def run() -> dict:
    config.ensure_dirs()
    inventory = discover.load_inventory()
    sources = {}
    for m in inventory["models"]:
        card = build_card(m)
        (config.MODEL_CARDS_DIR / f"{m['model_id']}.json").write_text(json.dumps(card, indent=2))
        (config.MODEL_CARDS_DIR / f"{m['model_id']}.md").write_text(to_markdown(card))
        sources[m["model_id"]] = card["narrative"]["source"]
    return {"models_documented": len(sources), "narrative_sources": sources,
            "claude_api_used": llm.available(),
            "output": config.rel(config.MODEL_CARDS_DIR)}


def load_card(model_id: str) -> dict | None:
    p = config.MODEL_CARDS_DIR / f"{model_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
