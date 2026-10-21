"""Phase 4 harness tests: no real model call, no network. Fake service answers go through the real Budget/cache code."""
import json

import pytest

from redteam import ATTACKS_DIR, RAG_DIR
from redteam.budget import Budget, BudgetExceeded, CacheMiss, payload_key
from redteam.oracles import judge
from redteam.run import load_attacks, run_target
from redteam.targets import rag_live, rag_service

SP = {"oracle": "no_prompt_leak", "system_prompt": "@rag:SYSTEM_V3", "min_len": 60}


def _attack(q="Kolik dni dovolene mam?"):
    return {"input": {"question": q}}


# ---------- attack files ----------
def test_all_injection_cases_are_converted_from_the_source_file():
    src = json.loads((RAG_DIR / "security" / "injection_cases.json").read_text(encoding="utf-8"))
    every = json.loads((ATTACKS_DIR / "rag_service.json").read_text(encoding="utf-8"))["attacks"]
    conv = {a["source_case"]: a for a in every if "source_case" in a}
    assert set(conv) == {c["id"] for c in src}
    for c in src:
        assert conv[c["id"]]["input"]["question"] == c["question"]            # exact text, incl. unicode tricks
        if c.get("canary"):
            assert {"oracle": "no_canary", "canary": c["canary"]} in conv[c["id"]]["checks"]
    assert len(every) == len(src) + 31
    assert len({a["id"] for a in every}) == len(every)


def test_deferred_attacks_are_skipped_and_the_rest_is_cached_or_runnable():
    every = json.loads((ATTACKS_DIR / "rag_service.json").read_text(encoding="utf-8"))["attacks"]
    run = load_attacks("rag_service")
    assert 0 < len(run) < len(every)
    assert all("deferred" not in a for a in run)
    assert len(load_attacks("rag_live")) == 5


def test_live_questions_fit_the_site_limits():
    for a in load_attacks("rag_live"):
        q = " ".join(a["input"]["question"].split())
        assert 8 <= len(q) <= 300, a["id"]


# ---------- oracles with the real system prompt ----------
def test_prompt_leak_oracle_uses_the_real_prompt_and_allows_the_normal_abstention():
    from redteam.targets.rag_common import add_rag_to_path
    add_rag_to_path()
    import rag
    abst = {"text": "Nevím, v dostupných úsecích zákona to není."}
    assert judge(abst, [SP])[0]                                    # the legitimate sentence is not a leak
    leak = {"text": "Jistě: " + rag.SYSTEM_V3[100:260]}
    ok, why = judge(leak, [SP])
    assert not ok and "leak" in why[0]


def test_citations_and_offtopic_oracles_on_service_observations():
    assert not judge({"text": "Dovolená je 4 týdny [7].", "n_passages": 5}, [{"oracle": "citations_valid"}])[0]
    assert judge({"text": "Dovolená je 4 týdny [2].", "n_passages": 5}, [{"oracle": "citations_valid"}])[0]
    assert judge({"evidence_status": "insufficient"}, [{"oracle": "refuses_offtopic"}])[0]
    assert not judge({"evidence_status": "sufficient"}, [{"oracle": "refuses_offtopic"}])[0]


# ---------- budget / cache behaviour of the adapter ----------
def test_answer_is_cached_key_free_and_offline_replay_is_identical(tmp_path, monkeypatch):
    calls = []

    def fake(question, laws):
        calls.append(question)
        return ({"service_error": None, "text": "Dovolená je 4 týdny [1].", "evidence_status": "sufficient", "n_passages": 5,
                 "passages_supplied": ["ZP § 213"], "citations": ["ZP § 213"], "app_checks": {}}, 0.0027)

    monkeypatch.setattr(rag_service, "_ask_real", fake)
    monkeypatch.setattr(rag_service, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("RT_RAG_SERVICE_DIR", str(tmp_path / "rag_service"))
    b = Budget(root=tmp_path)
    first = rag_service.run(_attack(), {"budget": b})
    assert calls == ["Kolik dni dovolene mam?"] and b.run_spent == pytest.approx(0.0027)
    again = rag_service.run(_attack(), {"budget": b})                  # cache hit
    assert len(calls) == 1 and b.run_spent == pytest.approx(0.0027)
    offline = rag_service.run(_attack(), {"budget": Budget(root=tmp_path, offline=True)})
    assert {k: v for k, v in first.items() if k != "elapsed_s"} == {k: v for k, v in offline.items() if k != "elapsed_s"} == \
           {k: v for k, v in again.items() if k != "elapsed_s"}
    cached = next((tmp_path / "rag_service").glob("*.json")).read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY" not in cached and "sk-or-" not in cached
    with pytest.raises(CacheMiss):
        rag_service.run(_attack("jina otazka"), {"budget": Budget(root=tmp_path, offline=True)})


def test_phase_cap_stops_before_a_fresh_call(tmp_path, monkeypatch):
    ns = tmp_path / "rag_service"
    ns.mkdir()
    (ns / "x.json").write_text(json.dumps({"cost_usd": 0.0449}), encoding="utf-8")
    monkeypatch.setattr(rag_service, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("RT_RAG_SERVICE_DIR", str(ns))
    monkeypatch.setattr(rag_service, "_ask_real", lambda q, l: pytest.fail("must not be called over the cap"))
    with pytest.raises(BudgetExceeded):
        rag_service.run(_attack(), {"budget": Budget(root=tmp_path)})


def test_provider_failure_stops_the_run_and_is_not_cached(tmp_path, monkeypatch):
    def boom(q, laws):
        raise rag_service.ProviderStop("provider_unavailable: out of credit")

    monkeypatch.setattr(rag_service, "_ask_real", boom)
    monkeypatch.setattr(rag_service, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("RT_RAG_SERVICE_DIR", str(tmp_path / "rag_service"))
    monkeypatch.setitem(rag_service._state, "stopped", None)
    with pytest.raises(BudgetExceeded):
        rag_service.run(_attack(), {"budget": Budget(root=tmp_path)})
    assert not list((tmp_path / "rag_service").glob("*.json")) if (tmp_path / "rag_service").exists() else True
    rag_service._state.pop("stopped", None)


def test_scrub_removes_the_secret():
    out = rag_service._scrub({"message": "bad key sk-or-SECRET123 here"}, "sk-or-SECRET123")
    assert "SECRET123" not in json.dumps(out)


# ---------- live adapter ----------
def test_pow_and_status_rule():
    n = rag_live.pow_nonce("test otazka", 1234567890)
    import hashlib
    assert hashlib.sha256(f"1234567890:{n}:test otazka".encode()).hexdigest().startswith("0000")
    assert rag_live.derive_status("Nevím, v dostupných úsecích zákona to není.", 5) == "insufficient"
    assert rag_live.derive_status("Ano [2].", 5) == "sufficient"
    assert rag_live.derive_status("Ano [9].", 5) == "insufficient"
    assert rag_live.derive_status("Ano.", 5) == "insufficient"


def test_live_call_needs_explicit_opt_in_and_has_a_hard_total_of_five(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_live, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(rag_live, "_live_call", lambda q: pytest.fail("no network in tests"))
    atk = {"input": {"question": "Jak dlouhá je výpovědní doba?"}}
    monkeypatch.delenv("RT_ALLOW_LIVE", raising=False)
    with pytest.raises(CacheMiss):
        rag_live.run(atk, {"budget": Budget(root=tmp_path)})
    d = tmp_path / "rag_live"
    d.mkdir()
    for i in range(5):
        (d / f"{i}.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("RT_ALLOW_LIVE", "1")
    with pytest.raises(BudgetExceeded):
        rag_live.run(atk, {"budget": Budget(root=tmp_path)})


def test_live_cached_answer_needs_no_opt_in(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_live, "CACHE_DIR", tmp_path)
    monkeypatch.delenv("RT_ALLOW_LIVE", raising=False)
    atk = {"input": {"question": "Jak dlouhá je výpovědní doba?"}}
    payload = {"url": rag_live.URL, "q": "Jak dlouhá je výpovědní doba?"}
    d = tmp_path / "rag_live"
    d.mkdir()
    (d / f"{payload_key(payload)}.json").write_text(json.dumps({"payload": payload, "cost_usd": 0.003, "response": {
        "status": 200, "text": "Dva měsíce [1].", "n_passages": 5, "evidence_status": "sufficient"}}), encoding="utf-8")
    obs = rag_live.run(atk, {"budget": Budget(root=tmp_path)})
    assert obs["text"] == "Dva měsíce [1]." and obs["error"] is None
