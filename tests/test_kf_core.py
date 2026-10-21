"""Harness against the real Kontrola faktur rules (read-only, in-memory store)."""
from redteam.run import load_attacks, run_target
from redteam.budget import Budget
from redteam.targets import kf_core


def test_attack_file_is_valid():
    attacks = load_attacks("kf_core")
    assert len(attacks) >= 10
    assert len({a["id"] for a in attacks}) == len(attacks)
    for a in attacks:
        assert a["checks"] and a["group"] and a["title"]


def test_clean_invoice_approves():
    assert kf_core.run({"input": {}})["decision"] == "APPROVE"


def test_known_bad_invoices_match_expected():
    """Sanity: the adapter reproduces the app's own expected decisions."""
    import json
    from redteam import KF_DIR
    expected = json.loads((KF_DIR / "data" / "expected.json").read_text(encoding="utf-8"))
    for name in ["02-zdrazeno", "04-cizi-ucet", "05-spatne-ico", "06-spatny-soucet"]:
        obs = kf_core.run({"input": {"base": f"{name}.json"}})
        assert obs["decision"] == expected[name]["decision"], name


def test_attacks_do_not_share_history():
    a = {"input": {}}
    assert kf_core.run(a)["decision"] == kf_core.run(a)["decision"] == "APPROVE"


def test_full_run_control_holds(tmp_path):
    results = run_target("kf_core", None, Budget(root=tmp_path))
    control = [r for r in results if r["group"] == "control"]
    assert control and all(r["defended"] for r in control)
