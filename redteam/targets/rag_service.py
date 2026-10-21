"""RAG-Demo answer pipeline (tools/service.py ask) run LOCALLY. This target costs real money, so it goes through Budget.

Attack input: {"question": str, "laws": null | [..]}
Observation: {"text": answer, "evidence_status", "n_passages", "passages_supplied", "citations": [ids], "service_error": None|code,
              "app_checks": {...}, "error": None}
How the money is kept safe:
  * Budget.call("rag_service", payload, fn, estimate_usd) caches the whole answer in cache/rag_service/ and stops at the cap.
  * The cached payload is only the question and the model/prompt fingerprint. The API key is read by RAG-Demo's own code from
    RAG-Demo/.env at call time, lives only in os.environ, and every string we cache is scrubbed of it.
  * RAG-Demo files are never written: rag.LLM_CACHE is redirected into cache/rag_service/ and embed_api is wrapped so that
    new query embeddings are kept in our own file instead of RAG-Demo/data/emb_cache.npz.
  * Offline (`--offline`): answers come from the cache only, nothing is imported or called.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from redteam import CACHE_DIR
from redteam.budget import BudgetExceeded, payload_key
from redteam.targets.rag_common import add_rag_to_path, short

NAMESPACE = "rag_service"
ESTIMATE_USD = 0.003          # per question; measured fresh cost is much lower, this only guards the cap check
FALLBACK_COST_USD = 0.0012    # RAG-Demo's own measurement per question, used if the provider sends no cost field
_state: dict = {}


class ProviderStop(RuntimeError):
    """Key out of credit, provider down or timeout. Not cached; the run stops instead of burning retries."""


def _scrub(obj, secret: str | None):
    if not secret:
        return obj
    return json.loads(json.dumps(obj, ensure_ascii=False).replace(secret, "<redacted>"))


def _prepare():
    """Import RAG-Demo code and redirect its writes into our cache folder. Returns (rag, service, meter)."""
    if "rag" in _state:
        return _state["rag"], _state["service"], _state["meter"]
    add_rag_to_path()
    import numpy as np
    import requests
    import rag
    import service

    root = Path(os.environ.get("RT_RAG_SERVICE_DIR", CACHE_DIR / NAMESPACE)) / "_internal"
    root.mkdir(parents=True, exist_ok=True)
    rag.LLM_CACHE = root / "llm_cache.json"       # RAG-Demo/data/llm_cache.json stays untouched
    rag._llm_cache = None
    meter = {"fresh_cost": 0.0, "fresh_calls": 0, "max_reasoning_tokens": 0, "usage": []}

    orig_llm = rag.llm

    def llm(system, user, model=None, reasoning=True):
        before = len(rag._llm_cache_get())
        text, usage = orig_llm(system, user, model, reasoning)
        if len(rag._llm_cache_get()) > before:     # a fresh paid call, not a cache hit
            c = usage.get("cost")
            meter["fresh_cost"] += float(c) if c is not None else FALLBACK_COST_USD / 4
            meter["fresh_calls"] += 1
            rt = ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")) or 0
            meter["max_reasoning_tokens"] = max(meter["max_reasoning_tokens"], rt)
            meter["usage"].append({"kind": "llm", "model": model, "prompt": usage.get("prompt_tokens"),
                                   "completion": usage.get("completion_tokens"), "reasoning": rt, "cost": c})
        return text, usage

    rag.llm = llm

    base_file = rag.ROOT / "data" / "emb_cache.npz"
    extra_file = root / "emb_extra.npz"
    cache = dict(np.load(base_file)) if base_file.exists() else {}      # read only
    if extra_file.exists():
        cache.update(dict(np.load(extra_file)))
    extra: dict = {}

    def embed_api(texts):
        todo = [t for t in dict.fromkeys(texts) if t not in cache]
        if todo and rag.offline():
            raise rag.OfflineCacheMiss(f"embedding not cached ({len(todo)} texts)")
        if todo:
            from dotenv import load_dotenv
            load_dotenv(rag.ROOT / ".env")
            for i in range(0, len(todo), 64):
                batch = todo[i:i + 64]
                r = requests.post("https://openrouter.ai/api/v1/embeddings", timeout=120,
                                  headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                                  json={"model": rag.EMB_MODEL, "input": batch})
                r.raise_for_status()
                body = r.json()
                usage = body.get("usage") or {}
                c = usage.get("cost")
                meter["fresh_cost"] += float(c) if c is not None else (usage.get("total_tokens") or 0) * 1e-8
                meter["usage"].append({"kind": "embedding", "tokens": usage.get("total_tokens"), "cost": c})
                for t, d in zip(batch, body["data"]):
                    v = np.array(d["embedding"], dtype=np.float32)
                    cache[t] = extra[t] = v / np.linalg.norm(v)
            np.savez(extra_file, **extra)
        return np.stack([cache[t] for t in texts])

    rag.embed_api = embed_api
    _state.update(rag=rag, service=service, meter=meter)
    return rag, service, meter


def credit_left() -> dict:
    """Free metadata call: how much budget the key still has (never prints the key)."""
    import requests
    rag, _, _ = _prepare()
    from dotenv import load_dotenv
    load_dotenv(rag.ROOT / ".env")
    r = requests.get("https://openrouter.ai/api/v1/key", timeout=30,
                     headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
    d = (r.json() or {}).get("data", {}) if r.ok else {}
    return {"http": r.status_code, "limit": d.get("limit"), "limit_remaining": d.get("limit_remaining"), "usage": d.get("usage")}


def _ask_real(question: str, laws) -> tuple[dict, float]:
    """The real pipeline. Returns (cacheable response, cost in USD)."""
    rag, service, meter = _prepare()
    meter.update(fresh_cost=0.0, fresh_calls=0)
    try:
        res = service.ask(question, laws=laws, timeout=120.0)
    except service.ServiceError as e:
        key = os.environ.get("OPENROUTER_API_KEY")
        if e.code in ("provider_unavailable", "provider_timeout"):      # not an answer: never cache it, stop the run
            raise ProviderStop(f"{e.code}: {_scrub(short(e.message, 200), key)} {_scrub(e.details, key)}") from None
        resp = {"service_error": e.code, "message": _scrub(short(e.message, 300), key), "text": "", "evidence_status": None,
                "n_passages": 0, "passages_supplied": [], "citations": [], "app_checks": {}}
        return resp, meter["fresh_cost"]
    key = os.environ.get("OPENROUTER_API_KEY")
    resp = {"service_error": None, "text": res.answer, "evidence_status": res.evidence_status,
            "n_passages": len(res.passages_supplied), "passages_supplied": res.passages_supplied,
            "citations": [c.id for c in res.citations], "rewritten_query": res.rewritten_query,
            "app_checks": res.checks.model_dump()}
    return _scrub(resp, key), meter["fresh_cost"]


def namespace_spent() -> float:
    d = Path(os.environ.get("RT_RAG_SERVICE_DIR", CACHE_DIR / NAMESPACE))
    return sum(float(json.loads(p.read_text(encoding="utf-8")).get("cost_usd", 0)) for p in d.glob("*.json"))


def payload_for(attack: dict) -> dict:
    inp = attack["input"]
    # fingerprint = what would change the answer: question, laws, models, answer prompt. Never a secret.
    add_rag_to_path()
    import rag
    return {"fn": "service.ask", "question": inp["question"], "laws": inp.get("laws"),
            "llm": rag.LLM_MODEL, "answer_model": rag.ANSWER_MODEL,
            "system_sha": hashlib.sha256(rag.SYSTEM_V3.encode()).hexdigest()[:12]}


def run(attack: dict, ctx=None) -> dict:
    budget = ctx["budget"]
    inp = attack["input"]
    payload = payload_for(attack)
    t0 = time.perf_counter()
    spent = namespace_spent()
    max_usd = float(os.environ.get("RT_RAG_SERVICE_MAX_USD", "0.045"))   # this phase only; the key has ~0.07 $ left
    cached = (Path(os.environ.get("RT_RAG_SERVICE_DIR", CACHE_DIR / NAMESPACE)) / f"{payload_key(payload)}.json").exists()
    if not cached and not budget.offline and spent + ESTIMATE_USD > max_usd:
        raise BudgetExceeded(f"phase 4 cap: {spent:.4f} $ already spent in {NAMESPACE}, limit {max_usd:.3f} $")
    if _state.get("stopped"):
        raise BudgetExceeded(_state["stopped"])
    try:
        resp = budget.call(NAMESPACE, payload, lambda: _ask_real(inp["question"], inp.get("laws")), estimate_usd=ESTIMATE_USD)
    except ProviderStop as e:
        _state["stopped"] = f"provider stopped answering ({e}); nothing more is called"
        raise BudgetExceeded(_state["stopped"]) from None
    obs = dict(resp)
    obs["error"] = None
    obs["elapsed_s"] = round(time.perf_counter() - t0, 2)
    return obs
