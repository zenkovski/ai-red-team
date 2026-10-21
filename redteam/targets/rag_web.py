"""RAG-Demo website target ("site"): three kinds of attack, selected by attack["input"]["kind"].

  xss      Playwright + a LOCAL static server over RAG-Demo/site (read-only). /api/* is mocked with page.route,
           every non-local request is aborted (d3 is served from a local copy), so nothing leaves the machine.
           input: {"kind":"xss", "mock": {"status": 200, "patch": {...}, "error": "..."}, "wait": "bot|err"}
           "{P}" inside any patched string is replaced with the payload (sets window.__pwned).
           obs: dialogs, pwned, injected_elements, page_errors
  hit_js   site/api/hit.js run in node with a fake Redis. input: {"kind":"hit_js","origin","method","body"|"body_raw"}
           "$PRESET0" in a body value = the first real preset question. obs: status, store_calls, calls
  headers  ONE passive GET of the live site (cached in cache/rag_web_live/, so at most one request per cache).
           obs: status, headers
"""
from __future__ import annotations

import functools
import http.server
import json
import subprocess
import threading
from pathlib import Path

from redteam import RAG_DIR, WORKSPACE
from redteam.targets.rag_common import expand, short

SITE = RAG_DIR / "site"
LIVE_URL = "https://lukas-rag.vercel.app/"
D3_LOCAL = WORKSPACE / "MG-Lab" / "repo" / "node_modules" / "d3" / "dist" / "d3.min.js"
HARNESS = Path(__file__).with_name("rag_hit_harness.cjs")
PAYLOAD = '<img src=x onerror="window.__pwned=1">'

_state: dict = {}


def _server(site_dir: str | None = None) -> str:
    """Local static server. site_dir lets the tests serve a deliberately broken copy (mutation control)."""
    key = site_dir or "default"
    if key not in _state:
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        handler = functools.partial(Quiet, directory=site_dir or str(SITE))
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _state[key] = f"http://127.0.0.1:{srv.server_address[1]}"
        _state[key + "_srv"] = srv
    return _state[key]


def _browser():
    if "browser" not in _state:
        from playwright.sync_api import sync_playwright
        _state["pw"] = sync_playwright().start()
        _state["browser"] = _state["pw"].chromium.launch()
    return _state["browser"]


def _subst(v, payload: str):
    if isinstance(v, str):
        return v.replace("{P}", payload)
    if isinstance(v, list):
        return [_subst(x, payload) for x in v]
    if isinstance(v, dict):
        return {k: _subst(x, payload) for k, x in v.items()}
    return v


def _base_answer() -> dict:
    d = json.loads((SITE / "data.json").read_text(encoding="utf-8"))
    q = next(x for x in d["questions"] if x.get("trace") and x.get("hits") and not x["answer"].startswith("Nevím"))
    return {"q": "Jak dlouhá je výpovědní doba?", "rewritten": q.get("rewritten", "x"), "hits": q["hits"], "trace": q["trace"],
            "answer": q["answer"], "remaining": 9}


def _run_xss(inp: dict) -> dict:
    base_url = _server(inp.get("site_dir"))
    ctx = _browser().new_context()
    page = ctx.new_page()
    dialogs, errors = [], []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.on("pageerror", lambda e: errors.append(short(e, 200)))

    def route_all(route):
        url = route.request.url
        if url.startswith(base_url):
            return route.continue_()
        if "d3.min.js" in url and D3_LOCAL.exists():
            return route.fulfill(path=str(D3_LOCAL), content_type="application/javascript")
        return route.abort()                                  # fonts, icons, analytics: not needed, never fetched

    page.route("**/*", route_all)
    mock = inp["mock"]
    payload = inp.get("payload", PAYLOAD)

    def api_ask(route):
        if mock.get("status", 200) != 200 or "error" in mock:
            body = {"error": _subst(mock.get("error", "chyba"), payload)}
        else:
            body = {**_base_answer(), **_subst(expand(mock.get("patch", {})), payload)}
        route.fulfill(status=mock.get("status", 200), content_type="application/json", body=json.dumps(body))

    page.route(f"{base_url}/api/ask", api_ask)            # registered after the catch-all, so it wins
    page.route(f"{base_url}/api/hit", lambda r: r.fulfill(status=204))
    try:
        page.goto(base_url + "/index.html", wait_until="load")
        page.wait_for_function("typeof D === 'object' && D && D.questions && typeof liveAsk === 'function'", timeout=20000)
        page.wait_for_timeout(800)                            # init() draws the graph after data.json arrives
        page.evaluate("""() => { const f = document.getElementById('liveForm');
            f.q.value = 'Jak dlouha je vypovedni doba pri vypovedi?'; liveAsk(f); }""")
        sel = ".msg.err" if inp.get("wait") == "err" else ".msg.bot"
        rendered = True
        try:
            page.wait_for_selector(sel, timeout=25000)
        except Exception:
            rendered = False                                  # the page broke instead of showing the answer
        page.wait_for_timeout(1200)                           # let any onerror/onload handler fire
        pwned = page.evaluate("window.__pwned")
        injected = page.evaluate("""() => document.querySelectorAll(
            '#log [onerror],#log [onload],#log script,#src [onerror],#src script,#gstatus [onerror],#gstatus script').length""")
        return {"dialogs": dialogs, "pwned": bool(pwned) or injected > 0, "injected_elements": injected,
                "page_errors": errors + ([] if rendered else ["answer never rendered (page stuck)"]), "text": short(page.inner_text("#log"), 400)}
    finally:
        ctx.close()


def _run_hit(inp: dict) -> dict:
    presets = json.loads((SITE / "api" / "_presets.json").read_text(encoding="utf-8"))
    body = expand(inp.get("body"))
    if isinstance(body, dict):
        body = {k: (v.replace("$PRESET0", presets[0]) if isinstance(v, str) else v) for k, v in body.items()}
    case = {"siteApiDir": str(SITE / "api"), "method": inp.get("method", "POST"),
            "headers": {"origin": inp["origin"]} if inp.get("origin") else {}, "body": expand(inp.get("body_raw", body))}
    p = subprocess.run(["node", str(HARNESS)], input=json.dumps(case), capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if p.returncode != 0 or not p.stdout.strip():
        return {"status": None, "error": f"node failed: {short(p.stderr)}"}
    obs = json.loads(p.stdout.strip().splitlines()[-1])
    if obs.get("error"):
        obs["error"] = f"handler threw: {short(obs['error'], 300)}"
    obs["text"] = short(json.dumps(obs.get("calls"), ensure_ascii=False), 600)
    return obs


def _run_headers(inp: dict, ctx) -> dict:
    import requests

    def fetch():
        r = requests.get(LIVE_URL, timeout=20, headers={"User-Agent": "redteam-passive-header-check/1.0"})
        return {"status": r.status_code, "headers": dict(r.headers)}, 0.0

    return ctx["budget"].call("rag_web_live", {"url": LIVE_URL, "method": "GET", "purpose": "passive header check"}, fetch)


def run(attack: dict, ctx=None) -> dict:
    inp = attack["input"]
    kind = inp["kind"]
    try:
        if kind == "xss":
            return _run_xss(inp)
        if kind == "hit_js":
            return _run_hit(inp)
        if kind == "headers":
            return _run_headers(inp, ctx)
        return {"error": f"unknown kind {kind}"}
    except Exception as e:
        from redteam.budget import CacheMiss
        if isinstance(e, CacheMiss):
            raise
        return {"error": f"{type(e).__name__}: {short(e, 300)}"}
