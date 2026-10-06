"""Reglas explícitas por valor/dimensión, sin reemplazos globales de caracteres."""
import json
from pathlib import Path
import unicodedata

ALIAS_FILE = Path(__file__).resolve().parents[3] / "config/mcba_aliases.json"


def canonical(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).upper().split()) or None


def load_rules(path=ALIAS_FILE):
    if not path.exists():
        return []
    rules = json.loads(path.read_text(encoding="utf-8"))["rules"]
    seen = set()
    for r in rules:
        if r["status"] not in {"observed", "validated", "manual_review"}:
            raise ValueError("Estado de alias inválido")
        k = (r["dimension"], canonical(r["source_value"]))
        if k in seen:
            raise ValueError("Alias duplicado; no permitir decisiones por orden")
        seen.add(k)
    return rules


def normalized_label(dimension, value, rules=None, allow_observed=False):
    label = canonical(value)
    applicable = {"validated", "observed"} if allow_observed else {"validated"}
    for r in rules if rules is not None else load_rules():
        if r["dimension"] == dimension and canonical(r["source_value"]) == label and r["status"] in applicable:
            return canonical(r["canonical_value"])
    return label


def normalization_rule(dimension, value, rules=None):
    for r in rules if rules is not None else load_rules():
        if r["dimension"] == dimension and canonical(r["source_value"]) == canonical(value):
            return ("explicit_alias:" + r["status"], "high" if r["status"] == "validated" else "pending")
    return ("unicode_nfkc_upper_trim", "high")
