"""Stage 1 - Discover agent.

Scans legacy_models/ for model source files (R, Python, SAS), works out what
each one is, and writes a structured inventory to outputs/inventory.json.

Method: deterministic static analysis (file headers, regular expressions and
Python's ast module). No code from the scanned files is ever executed here.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
from datetime import date

from core import config, state

LANGUAGES = {".r": "R", ".py": "Python", ".sas": "SAS"}

METHOD_PATTERNS = [
    (r"glm\s*\(.*binomial", "Logistic regression (GLM, binomial/logit)"),
    (r"proc\s+logistic", "Logistic regression (SAS PROC LOGISTIC)"),
    (r"LogisticRegression\s*\(", "Logistic regression (scikit-learn)"),
    (r"GradientBoostingClassifier\s*\(", "Gradient boosting (scikit-learn)"),
    (r"RandomForestClassifier\s*\(", "Random forest (scikit-learn)"),
    (r"DecisionTreeClassifier\s*\(", "Decision tree (scikit-learn)"),
]

HEADER_RE = re.compile(r"^[\s#/*]*([A-Z_]{3,}):\s*(.+?)\s*(\*/)?$")


def parse_header(text: str) -> dict:
    meta = {}
    for line in text.splitlines()[:30]:
        m = HEADER_RE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
    return meta


def detect_methodology(text: str) -> str:
    flat = " ".join(text.split())
    for pattern, name in METHOD_PATTERNS:
        if re.search(pattern, flat, flags=re.IGNORECASE):
            return name
    return "Unknown"


def _r_string_vector(text: str, var: str) -> list[str]:
    m = re.search(rf"{var}\s*<-\s*c\(([^)]*)\)", text)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def _resolve_py_list(node: ast.AST) -> list[str] | None:
    """Resolve list literals, config.X references and '+' concatenations without executing code."""
    if isinstance(node, ast.List):
        vals = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return vals
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "config":
        val = getattr(config, node.attr, None)
        return list(val) if isinstance(val, (list, tuple)) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _resolve_py_list(node.left), _resolve_py_list(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def extract_features_and_target(text: str, language: str) -> tuple[list[str], str | None]:
    if language == "R":
        target = re.search(r'target\s*<-\s*"([^"]+)"', text)
        numeric = _r_string_vector(text, "numeric_vars")
        block = re.search(r"factor_levels\s*<-\s*list\((.*?)\n\)", text, flags=re.S)
        factors = re.findall(r"^\s*(\w+)\s*=\s*c\(", block.group(1), flags=re.M) if block else []
        return numeric + factors, target.group(1) if target else None
    if language == "Python":
        tree = ast.parse(text)
        features, target = [], None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name == "FEATURES":
                    features = _resolve_py_list(node.value) or []
                elif name == "TARGET" and isinstance(node.value, ast.Constant):
                    target = node.value.value
        return features, target
    if language == "SAS":
        m = re.search(r"model\s+(\w+)\s*=\s*([^/;]+)", text, flags=re.IGNORECASE)
        if m:
            return m.group(2).split(), m.group(1)
    return [], None


def related_artifacts(model_id: str) -> list[str]:
    if not config.LEGACY_ARTIFACTS.exists():
        return []
    return sorted(p.name for p in config.LEGACY_ARTIFACTS.glob(f"{model_id}_*"))


def risk_tier(meta: dict) -> str:
    use = (meta.get("use", "") + " " + meta.get("purpose", "")).lower()
    if any(k in use for k in ["approval", "pricing", "provision", "capital"]):
        return "Tier 1 - material (customer decisions / financial reporting)"
    if any(k in use for k in ["collection", "limit", "early"]):
        return "Tier 2 - moderate"
    return "Tier 3 - low"


def documentation_age_years(meta: dict) -> float | None:
    m = re.match(r"(\d{4})-(\d{2})", meta.get("last_review", ""))
    if not m:
        return None
    reviewed = date(int(m.group(1)), int(m.group(2)), 1)
    return round((date.today() - reviewed).days / 365.25, 1)


def scan_file(path) -> dict:
    text = path.read_text(errors="replace")
    language = LANGUAGES[path.suffix.lower()]
    meta = parse_header(text)
    features, target = extract_features_and_target(text, language)
    model_id = meta.get("model_id", path.stem)
    artifacts = related_artifacts(model_id)
    if language == "SAS":
        executable, how = False, "Not executable here (no SAS licence) - documentation only"
    elif language == "R":
        if shutil.which("Rscript"):
            executable, how = True, "Rscript available locally"
        elif any("_r_" in a for a in artifacts):
            executable, how = True, "Rscript not found; recorded R outputs available"
        else:
            executable, how = False, "Rscript not found and no recorded outputs"
    else:
        executable, how = True, "Python"
    doc_age = documentation_age_years(meta)
    return {
        "model_id": model_id,
        "model_name": meta.get("model_name", path.stem),
        "owner": meta.get("owner"),
        "purpose": meta.get("purpose"),
        "business_use": meta.get("use"),
        "language": language,
        "methodology": detect_methodology(text),
        "target_variable": target,
        "input_features": features,
        "n_features": len(features),
        "source_file": config.rel(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "lines_of_code": len(text.splitlines()),
        "last_documentation_review": meta.get("last_review"),
        "documentation_age_years": doc_age,
        "documentation_stale": bool(doc_age is not None and doc_age > 1.0),
        "risk_tier": risk_tier(meta),
        "executable": executable,
        "execution_note": how,
        "artifacts": artifacts,
        "notes": meta.get("note"),
    }


def run() -> dict:
    config.ensure_dirs()
    files = sorted(p for p in config.LEGACY_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in LANGUAGES)
    models = [scan_file(p) for p in files]
    inventory = {
        "generated_at": state.now(),
        "generated_by": "Discover agent (deterministic static analysis, no AI)",
        "scanned_folder": config.rel(config.LEGACY_DIR),
        "n_models": len(models),
        "models": models,
    }
    config.INVENTORY_FILE.write_text(json.dumps(inventory, indent=2))
    return {
        "models_discovered": len(models),
        "by_language": {lang: sum(m["language"] == lang for m in models) for lang in set(LANGUAGES.values())},
        "stale_documentation": sum(m["documentation_stale"] for m in models),
        "output": config.rel(config.INVENTORY_FILE),
    }


def load_inventory() -> dict:
    return json.loads(config.INVENTORY_FILE.read_text())


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
