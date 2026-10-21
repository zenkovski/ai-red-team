"""Tests of the RAG harness itself (phase 3): attack files are sane, the new oracles judge known cases correctly,
and the adapters can tell a defended target from a broken one (mutation controls). Read-only on RAG-Demo."""
import shutil

import pytest

from redteam import RAG_DIR
from redteam.oracles import ORACLES, judge
from redteam.run import load_attacks
from redteam.targets import rag_common, rag_mcp, rag_rest, rag_web

TARGETS = ["rag_mcp", "rag_rest", "rag_web"]


# ---------- attack files ----------
def test_attack_files_are_valid_and_big_enough():
    total = 0
    for t in TARGETS:
        attacks = load_attacks(t)
        total += len(attacks)
        ids = [a["id"] for a in attacks]
        assert len(ids) == len(set(ids)), t
        for a in attacks:
            assert a["group"] and a["title"] and a["checks"] and a.get("severity") in ("High", "Medium", "Low"), a["id"]
            for c in a["checks"]:
                assert c["oracle"] in ORACLES, (a["id"], c)
    assert total >= 40


def test_each_target_has_a_control_attack():
    for t in TARGETS:
        assert any(a["group"] == "control" for a in load_attacks(t)), t


def test_expand_markers():
    assert rag_common.expand({"$repeat": ["ab", 3]}) == "ababab"
    assert rag_common.expand({"a": [{"$repeat": ["x", 2]}]}) == {"a": ["xx"]}
    assert rag_common.expand({"$float": "nan"}) != rag_common.expand({"$float": "nan"})  # NaN


# ---------- new oracles ----------
def test_text_absent_and_field_equals():
    assert judge({"text": "all fine"}, [{"oracle": "text_absent", "needles": ["root:"]}])[0]
    assert not judge({"text": "root:x:0:0"}, [{"oracle": "text_absent", "needles": ["root:"]}])[0]
    assert judge({"store_calls": 0}, [{"oracle": "field_equals", "field": "store_calls", "value": 0}])[0]
    assert not judge({"store_calls": 1}, [{"oracle": "field_equals", "field": "store_calls", "value": 0}])[0]


def test_header_oracles():
    ok = {"headers": {"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'"}}
    assert judge(ok, [{"oracle": "header_present", "name": "content-security-policy"}, {"oracle": "framing_protected"},
                      {"oracle": "header_contains", "name": "X-Content-Type-Options", "any_of": ["nosniff"]}])[0]
    bad = {"headers": {"Server": "x"}}
    assert not judge(bad, [{"oracle": "header_present", "name": "Content-Security-Policy"}])[0]
    assert not judge(bad, [{"oracle": "framing_protected"}])[0]
    assert judge({"headers": {"X-Frame-Options": "DENY"}}, [{"oracle": "framing_protected"}])[0]


def test_timing_oracle():
    chk = [{"oracle": "timing_indistinguishable", "max_rel_diff": 0.10}]
    assert judge({"median_a_ms": 3.0, "median_b_ms": 3.1, "n": 100}, chk)[0]
    assert not judge({"median_a_ms": 4.0, "median_b_ms": 3.0, "n": 100}, chk)[0]       # 25 % slower: a leak
    assert not judge({}, chk)[0]


def test_tool_error_page_error_elapsed():
    assert judge({"is_error": True}, [{"oracle": "tool_error"}])[0]
    assert not judge({"is_error": False}, [{"oracle": "tool_error"}])[0]
    assert not judge({"page_errors": ["boom"]}, [{"oracle": "no_page_error"}])[0]
    assert judge({"page_errors": []}, [{"oracle": "no_page_error"}])[0]
    assert not judge({"elapsed_s": 30}, [{"oracle": "elapsed_below", "seconds": 20}])[0]


# ---------- rest adapter ----------
A = lambda **k: {"input": k}


def test_rest_control_and_auth():
    assert rag_rest.run(A(path="/api/v1/documents/ZP%20%C2%A7%2051%20odst.%202"))["status"] == 200
    assert rag_rest.run(A(path="/api/v1/documents/x", key="none"))["status"] == 401
    assert rag_rest.run(A(path="/api/v1/documents/x", key="wrong"))["status"] == 401


def test_rest_non_ascii_key_fixed_rt_rag_01():
    """RT-RAG-01 was a 500 on a non-ASCII key; fixed in RAG-Demo 5f76e41, now 401."""
    obs = rag_rest.run(A(path="/api/v1/documents/x", key="none", headers_latin1={"X-API-Key": "é"}))
    assert obs["status"] == 401
    # the oracle still flags a 500 if it ever comes back
    assert not judge({"status": 500}, [{"oracle": "http_status_in", "allowed": [401]}])[0]


def test_rest_traversal_is_not_found():
    obs = rag_rest.run(A(path="/api/v1/documents/..%2f..%2f.env"))
    assert obs["status"] == 404 and "OPENROUTER" not in obs["text"]


def test_rest_never_uses_the_real_key_or_network():
    assert rag_rest.os.environ["RAG_OFFLINE"] == "1"
    assert rag_rest.os.environ["RAG_API_KEYS"] == rag_rest.TEST_KEY


# ---------- mcp adapter ----------
def test_mcp_control_and_traversal():
    ok = rag_mcp.run({"input": {"tool": "get_document", "args": {"id": "ZP § 51 odst. 2"}}})
    assert ok["is_error"] is False and ok["error"] is None
    bad = rag_mcp.run({"input": {"tool": "get_document", "args": {"id": "../../.env"}}})
    assert bad["is_error"] is True and "OPENROUTER" not in bad["text"]
    assert judge(bad, [{"oracle": "tool_error"}])[0]


# ---------- web adapter ----------
def test_hit_js_control_and_foreign_string():
    ctl = rag_web.run({"input": {"kind": "hit_js", "origin": "https://lukas-rag.vercel.app", "body": {"q": "$PRESET0"}}})
    assert ctl["status"] == 204 and ctl["store_calls"] == 1
    foreign = rag_web.run({"input": {"kind": "hit_js", "origin": "https://lukas-rag.vercel.app", "body": {"q": "foreign"}}})
    assert foreign["status"] == 204 and foreign["store_calls"] == 0
    evil = rag_web.run({"input": {"kind": "hit_js", "origin": "https://evil.com", "body": {"q": "$PRESET0"}}})
    assert evil["status"] == 403 and evil["store_calls"] == 0


def test_xss_adapter_detects_a_real_hole(tmp_path):
    """Mutation control: break esc() in a copy of the site; the harness must see the script run."""
    site = tmp_path / "site"
    shutil.copytree(RAG_DIR / "site", site)
    html = (site / "index.html").read_text(encoding="utf-8")
    marker = 'const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;"}[c]));'
    assert marker in html, "esc() changed in the app, update the mutation control"
    (site / "index.html").write_text(html.replace(marker, "const esc = s => String(s);"), encoding="utf-8")
    attack = {"kind": "xss", "site_dir": str(site), "mock": {"patch": {"answer": "Ahoj {P} [1]"}}}
    obs = rag_web.run({"input": attack})
    assert obs["pwned"] is True
    assert not judge(obs, [{"oracle": "no_script_exec"}])[0]


def test_xss_adapter_passes_the_real_site():
    obs = rag_web.run({"input": {"kind": "xss", "mock": {"patch": {"answer": "Ahoj {P} [1]"}}}})
    assert obs["pwned"] is False and obs["dialogs"] == [] and "error" not in obs
