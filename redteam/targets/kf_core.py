"""Kontrola faktur, rules only. Calls faktury.pipeline.process directly. No AI, no network, free.

Attack input:
  invoice   : patch over the base invoice (keys replace base keys); or full invoice if base is null
  base      : file name in ../Kontrola-Faktur/data/invoices/ (default 01-v-poradku.json)
  preload   : list of invoices processed first in the same store (duplicates, split billing)
  raw_text  : optional document text, goes to the guard
Observation: {"decision": "APPROVE|REVIEW|STOP", "codes": [...], "error": None | "Type: msg"}
"""
from __future__ import annotations

import json
import sys

from redteam import KF_DIR

if str(KF_DIR) not in sys.path:
    sys.path.insert(0, str(KF_DIR))

from faktury.models import Invoice  # noqa: E402
from faktury.pipeline import Books, process  # noqa: E402
from faktury.store import Store  # noqa: E402

INVOICES = KF_DIR / "data" / "invoices"
_books: Books | None = None


def books() -> Books:
    global _books
    if _books is None:
        _books = Books.load(KF_DIR / "data")
    return _books


def build_invoice(spec: dict) -> dict:
    base_name = spec.get("base", "01-v-poradku.json")
    base = json.loads((INVOICES / base_name).read_text(encoding="utf-8")) if base_name else {}
    return {**base, **spec.get("invoice", {})}


def run(attack: dict, ctx=None) -> dict:
    inp = attack["input"]
    store = Store(":memory:")  # fresh history per attack, attacks never leak into each other
    try:
        for pre in inp.get("preload", []):
            process(Invoice.from_dict(build_invoice(pre)), books(), store)
        inv = Invoice.from_dict(build_invoice(inp))
        res = process(inv, books(), store, raw_text=inp.get("raw_text"))
    except Exception as e:  # a crash is an observation, not a harness failure
        return {"decision": None, "codes": [], "error": f"{type(e).__name__}: {e}"}
    return {"decision": res.decision.value, "codes": [f.code for f in res.findings], "error": None}
