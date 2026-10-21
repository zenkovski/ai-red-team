"""RAG-Demo REST API (tools/api.py) in-process through FastAPI TestClient. Offline, free, key set by us.

Attack input (one request):
  method, path, json | raw_body | stream_bytes, headers (dict, "{KEY}" = the valid test key),
  headers_latin1 (dict, value is encoded as latin-1 bytes, to send non-ASCII header bytes)
  key: "valid" | "none" | any literal (sent as X-API-Key; "{KEY}" substitution works here too)
Timing attack: input {"timing": {"path": ..., "n": 300}} compares an almost right key (only last char wrong)
with a totally wrong key of the same length, interleaved, and reports medians. Measures only.
Observation: {"status", "text", "code" (error.code from the body), "request_id"} / timing fields.
"""
from __future__ import annotations

import json
import os
import statistics
import time

from redteam.targets.rag_common import add_rag_to_path, expand, short

TEST_KEY = "redteam-test-key-0123456789abcdef"
os.environ["RAG_OFFLINE"] = "1"          # never a paid call from this target
os.environ["RAG_API_KEYS"] = TEST_KEY

add_rag_to_path()
from fastapi.testclient import TestClient  # noqa: E402

import api  # noqa: E402  (RAG-Demo/tools/api.py, imported, never modified)

import logging  # noqa: E402

logging.getLogger("rag.api").setLevel(logging.CRITICAL)   # the app logs a trace for every 500; we record the 500 itself
_client = TestClient(api.app, raise_server_exceptions=False)


def _headers(inp: dict) -> dict:
    h = {k: v.replace("{KEY}", TEST_KEY) for k, v in inp.get("headers", {}).items()}
    key = inp.get("key", "valid")
    if key == "valid":
        h["X-API-Key"] = TEST_KEY
    elif key != "none":
        h["X-API-Key"] = key.replace("{KEY}", TEST_KEY)
    for k, v in inp.get("headers_latin1", {}).items():
        h[k] = v.encode("latin-1")
    return h


def _timing(inp: dict) -> dict:
    t = inp["timing"]
    n = int(t.get("n", 300))
    almost = TEST_KEY[:-1] + ("0" if TEST_KEY[-1] != "0" else "1")
    wrong = "x" * len(TEST_KEY)
    path = t["path"]
    a, b = [], []
    for _ in range(20):  # warm up
        _client.get(path, headers={"X-API-Key": wrong})
    for i in range(n):
        for key, bucket in ((almost, a), (wrong, b)) if i % 2 == 0 else ((wrong, b), (almost, a)):
            t0 = time.perf_counter_ns()
            r = _client.get(path, headers={"X-API-Key": key})
            bucket.append((time.perf_counter_ns() - t0) / 1e6)
            assert r.status_code == 401
    return {"status": 401, "n": n, "median_a_ms": statistics.median(a), "median_b_ms": statistics.median(b),
            "text": "timing only, request count %d" % (2 * n)}


def run(attack: dict, ctx=None) -> dict:
    inp = attack["input"]
    try:
        if "timing" in inp:
            return _timing(inp)
        kw: dict = {"headers": _headers(inp)}
        if "json" in inp:
            kw["json"] = expand(inp["json"])
        if "raw_body" in inp:
            kw["content"] = expand(inp["raw_body"])
        if "stream_bytes" in inp:   # chunked upload without Content-Length
            total, chunk = int(inp["stream_bytes"]), 65536
            body = json.dumps({"query": "a" * total}).encode()
            kw["content"] = (body[i:i + chunk] for i in range(0, len(body), chunk))
            kw["headers"]["Content-Type"] = "application/json"
        r = _client.request(inp.get("method", "GET"), inp["path"], **kw)
        try:
            code = (r.json().get("error") or {}).get("code")
        except Exception:
            code = None
        return {"status": r.status_code, "code": code, "text": short(r.text, 1500), "request_id": r.headers.get("x-request-id"),
                "rid_echoed": r.headers.get("x-request-id") == inp.get("headers", {}).get("x-request-id")}
    except Exception as e:  # the harness crashed, not the app: counts as not defended and shows up
        return {"status": None, "text": "", "error": f"{type(e).__name__}: {short(e)}"}
