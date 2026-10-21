"""LIVE site https://lukas-rag.vercel.app/api/ask. At most 5 questions TOTAL, ever (the site allows 10 per IP per day and its key is almost empty).

Safety, all enforced here and not by good intentions:
  * every answer is cached in cache/rag_live/ (Budget namespace "rag_live"); a repeated run costs nothing and sends nothing
  * a NEW live question needs the env var RT_ALLOW_LIVE=1, otherwise CacheMiss (a normal run never goes live by accident)
  * LIVE_MAX_TOTAL = 5 cached questions; the 6th is refused with BudgetExceeded
  * only HTTP 200 answers are cached/counted; a 429/503 stops the run and is not retried
Same request the page sends: proof of work, Origin and X-Rag-Client headers (our own app, the normal client).
Observation: {"text", "status", "n_passages", "evidence_status" (derived with the same rule as service.py), "rewritten", "error"}
"""
from __future__ import annotations

import hashlib
import os
import re
import time

import requests

from redteam import CACHE_DIR
from redteam.budget import BudgetExceeded, CacheMiss
from redteam.targets.rag_common import short

NAMESPACE = "rag_live"
URL = "https://lukas-rag.vercel.app/api/ask"
LIVE_MAX_TOTAL = 5
EST_COST_USD = 0.003          # the site's key pays, not ours; counted in the ledger as a conservative estimate


def pow_nonce(q: str, ts: int) -> str:
    """sha256(f"{ts}:{nonce}:{q}") must start with 4 hex zeros (same rule as site/api/ask.js and the page)."""
    n = 0
    while not hashlib.sha256(f"{ts}:{n}:{q}".encode()).hexdigest().startswith("0000"):
        n += 1
    return str(n)


def derive_status(answer: str, n_passages: int) -> str:
    """Same definition as tools/service.py: sufficient = not 'Nevim', cites at least one valid marker, no invalid marker."""
    cited = {int(x) for x in re.findall(r"\[(\d+)\]", answer)}
    bad = [c for c in cited if not 1 <= c <= n_passages]
    abstained = answer.strip().lower().startswith("nevím")
    return "sufficient" if (not abstained and cited and not bad) else "insufficient"


def _live_call(q: str) -> tuple[dict, float]:
    ts = int(time.time() * 1000)
    r = requests.post(URL, timeout=90, json={"q": q, "ts": ts, "nonce": pow_nonce(q, ts), "website": ""},
                      headers={"Origin": "https://lukas-rag.vercel.app", "X-Rag-Client": "web", "Content-Type": "application/json"})
    try:
        d = r.json()
    except Exception:
        d = {}
    if r.status_code != 200:
        raise BudgetExceeded(f"live site answered {r.status_code}: {short(d.get('error', r.text), 200)}. Stopped, no retry.")
    ans = d.get("answer", "")
    return {"status": 200, "text": ans, "n_passages": len(d.get("hits", [])), "evidence_status": derive_status(ans, len(d.get("hits", []))),
            "rewritten": d.get("rewritten"), "remaining": d.get("remaining")}, EST_COST_USD


def run(attack: dict, ctx=None) -> dict:
    budget = ctx["budget"]
    q = " ".join(attack["input"]["question"].split())
    payload = {"url": URL, "q": q}
    d = CACHE_DIR / NAMESPACE
    from redteam.budget import payload_key
    cached = (d / f"{payload_key(payload)}.json").exists()
    if not cached and not budget.offline:
        if os.environ.get("RT_ALLOW_LIVE") != "1":
            raise CacheMiss("live question not cached and RT_ALLOW_LIVE=1 is not set")
        if len(list(d.glob("*.json"))) >= LIVE_MAX_TOTAL:
            raise BudgetExceeded(f"live limit reached: {LIVE_MAX_TOTAL} questions in total, ever")
    obs = dict(budget.call(NAMESPACE, payload, lambda: _live_call(q), estimate_usd=EST_COST_USD))
    obs["error"] = None
    return obs
