import pytest

from redteam.budget import Budget, BudgetExceeded, CacheMiss


def test_cache_makes_second_call_free(tmp_path):
    b = Budget(cap_usd=0.05, root=tmp_path)
    calls = []
    fn = lambda: (calls.append(1) or {"answer": 42}, 0.01)
    assert b.call("ns", {"q": 1}, fn) == {"answer": 42}
    assert b.call("ns", {"q": 1}, fn) == {"answer": 42}
    assert len(calls) == 1
    assert b.spent == pytest.approx(0.01)


def test_cap_is_hard_and_survives_restart(tmp_path):
    Budget(cap_usd=0.02, root=tmp_path).call("ns", {"q": 1}, lambda: ({}, 0.02))
    b2 = Budget(cap_usd=0.02, root=tmp_path)  # new run, same ledger
    with pytest.raises(BudgetExceeded):
        b2.call("ns", {"q": 2}, lambda: ({}, 0.001))


def test_estimate_blocks_before_spending(tmp_path):
    b = Budget(cap_usd=0.05, root=tmp_path)
    with pytest.raises(BudgetExceeded):
        b.call("ns", {"q": 1}, lambda: ({}, 0.0), estimate_usd=0.06)


def test_offline_never_calls(tmp_path):
    b = Budget(root=tmp_path, offline=True)
    with pytest.raises(CacheMiss):
        b.call("ns", {"q": 1}, lambda: pytest.fail("offline must not call"))
