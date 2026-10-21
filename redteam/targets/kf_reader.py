"""Kontrola faktur, AI reader (DeepSeek Flash via OpenRouter). COSTS MONEY: every call goes through Budget.call.

Flow per attack: text -> extract_openrouter.read_text (cached in Red-Team/cache/kf_reader/ by Budget) -> fields the AI
read -> the same invoice through faktury.pipeline.process (rules + guard on the raw text, as the app does).

Key handling: read from Kontrola-Faktur/.env at runtime into the environment variable the module expects.
It is never written to a file, a cache payload or the output.

Attack input: {"text": invoice text, "printed": {field: value as printed}, "target": field}
Observation: {"fields": {AI output}, "decision", "codes", "usage": {...}, "error"}
"""
from __future__ import annotations

import hashlib
import importlib
import os
import sys

from redteam import KF_DIR
from redteam.targets import kf_core

if str(KF_DIR) not in sys.path:
    sys.path.insert(0, str(KF_DIR))

NAMESPACE = "kf_reader"
ESTIMATE_USD = 0.002  # pessimistic guard before each real call; real cost is measured from usage.cost
_state: dict = {}


def _load_key() -> None:
    if os.environ.get("OPENROUTER_API_KEY") and "fake" not in os.environ["OPENROUTER_API_KEY"]:
        return
    env = KF_DIR / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            os.environ["OPENROUTER_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
            return
    raise RuntimeError("OPENROUTER_API_KEY not found in Kontrola-Faktur/.env")


def _reader():
    """The module with the real network function (kf_mcp may have patched it earlier in the same process)."""
    if "mod" not in _state:
        from faktury import extract_openrouter
        _state["mod"] = importlib.reload(extract_openrouter)
    return _state["mod"]


class InfraError(RuntimeError):
    pass


def run(attack: dict, ctx=None) -> dict:
    from faktury.extract import ExtractionError, to_invoice
    from faktury.models import Invoice  # noqa: F401
    from faktury.pipeline import process
    from faktury.store import Store

    budget = ctx["budget"]
    text = attack["input"]["text"]
    mod = _reader()
    payload = {"model": mod.MODEL, "prompt_version": mod.PROMPT_VERSION,
               "system_sha": hashlib.sha256(mod.SYSTEM.encode()).hexdigest()[:12], "text": text}

    def fn():
        _load_key()
        try:
            _, raw, seconds, _, usage = mod.read_text(text, cache_dir=None)
        except ExtractionError as e:
            msg = str(e)
            if "OpenRouter odmítl" in msg or "neodpovídá" in msg or "Chybí" in msg:
                raise InfraError(msg)  # 402 no credit, 401, network: stop, never cache, never count as a verdict
            return {"extraction_failed": msg, "usage": {}}, 0.0
        return {"raw": raw, "usage": usage, "seconds": round(seconds, 2)}, float(usage.get("cost") or 0.0)

    try:
        resp = budget.call(NAMESPACE, payload, fn, estimate_usd=ESTIMATE_USD)
    except InfraError as e:
        return {"fields": {}, "decision": None, "codes": [], "error": f"infra: {e}"}

    if "extraction_failed" in resp:  # the app answers REVIEW (EXTRACTION_FAILED) in this case
        return {"fields": {}, "decision": "REVIEW", "codes": ["EXTRACTION_FAILED"], "usage": {}, "error": None,
                "note": resp["extraction_failed"][:120]}
    raw = resp["raw"]
    try:
        inv = to_invoice(raw)
        res = process(inv, kf_core.books(), Store(":memory:"), raw_text=text)
    except Exception as e:  # e.g. NaN from the AI crashes the rules: reported, not hidden
        return {"fields": raw, "decision": None, "codes": [], "usage": resp.get("usage", {}),
                "error": f"{type(e).__name__}: {e}"}
    return {"fields": raw, "decision": res.decision.value, "codes": [f.code for f in res.findings],
            "usage": resp.get("usage", {}), "error": None}
