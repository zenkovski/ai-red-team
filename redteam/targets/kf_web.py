"""Kontrola faktur, web page XSS test with Playwright against the LOCAL page (free, no network, no AI).

How the page is served: web/app.py (FastAPI) is run in a thread by uvicorn on a free local port, exactly how the
project runs it (`uvicorn web.app:app`). The public static version (site/index.html + Pyodide) has the same render
code; it differs only in loading Pyodide from a CDN, so it is not driven here (needs network, same JS).
All requests to other hosts (fonts, icons) are blocked.

The "AI read" is replaced by an intercepted `/api/read/<id>` answer that contains the attacker's invoice,
which is what a hostile PDF would produce after the AI copied its text. Nothing is paid.

Attack input:
  field   : invoice_number | sku | qty | unit_price | note | po_number | bank_account | issue_date | supplier_ico |
            document_text | reader | seconds | image | supplier_name (poisoned books)
  payload : string put into that field
  via     : "read" (arrives from the AI read) | "typed" (typed into the form by the visitor)
  check   : click "Zkontrolovat" afterwards so the result panel renders too
Observation: {"dialogs": [...], "pwned": bool, "page_errors": [...], "form_rendered": bool, "error": None}
"""
from __future__ import annotations

import socket
import threading
import time

from redteam.targets import kf_mcp

_srv: dict = {}


def _server() -> str:
    if _srv:
        return _srv["url"]
    import uvicorn
    c = kf_mcp.setup()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(c["web"].app, host="127.0.0.1", port=port, log_level="critical"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    _srv.update(url=f"http://127.0.0.1:{port}", server=server, thread=t)
    return _srv["url"]


def _invoice(field: str, payload: str) -> dict:
    inv = dict(kf_mcp.VALID)
    inv["lines"] = [dict(x) for x in inv["lines"]]
    if field in ("sku", "qty", "unit_price"):
        inv["lines"][0][field] = payload
    elif field in inv:
        inv[field] = payload
    return inv


def run(attack: dict, ctx=None) -> dict:
    from playwright.sync_api import sync_playwright

    inp = attack["input"]
    field, payload, via = inp["field"], inp["payload"], inp.get("via", "read")
    url = _server()
    obs = {"dialogs": [], "pwned": False, "page_errors": [], "form_rendered": False, "error": None}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.on("dialog", lambda d: (obs["dialogs"].append(d.message), d.dismiss()))
            page.on("pageerror", lambda e: obs["page_errors"].append(str(e)[:120]))

            def route(r):
                u = r.request.url
                if not u.startswith(url):
                    return r.abort()
                if "/api/read/" in u:
                    hostile = via == "read" and field not in ("document_text", "reader", "seconds", "image", "supplier_name")
                    data = {"invoice": _invoice(field, payload) if hostile else _invoice("invoice_number", "FV-RT-1"), "seconds": 1.2, "cached": False, "source": "pdf",
                            "reader": "DeepSeek", "document_text": None}
                    if field in ("document_text", "reader", "seconds", "image"):
                        data[field] = payload
                    return r.fulfill(json=data)
                if u.endswith("/api/books") and field == "supplier_name":
                    books = c_books()
                    books["suppliers"][0]["name"] = payload
                    return r.fulfill(json=books)
                return r.continue_()

            def c_books():
                import json
                from urllib.request import urlopen
                return json.loads(urlopen(url + "/api/books").read())

            page.route("**/*", route)
            page.goto(url + "/", wait_until="domcontentloaded")
            page.wait_for_selector("#form input", timeout=15000)
            obs["form_rendered"] = True
            if via == "typed":
                sel = {"note": "textarea[data-k=note]", "sku": None}.get(field) or f"input[data-k={field}]"
                if field in ("qty", "unit_price"):
                    sel = f"input[data-line='0'][data-lk={field}]"
                page.fill(sel, payload)
                page.dispatch_event(sel, "change")
            if inp.get("check"):
                page.click("#check")
            page.wait_for_timeout(800)
            obs["pwned"] = bool(page.evaluate("() => window.__pwned || window.__pwned2 || false"))
            browser.close()
    except Exception as e:
        obs["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return obs
