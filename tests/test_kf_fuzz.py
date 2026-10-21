"""Property tests (Hypothesis) for the rules of Kontrola faktur. Free, no AI.

A property that fails on the real app is a FINDING (see findings/RT-KF-*.md). Such a test is marked
xfail with the finding id: the suite stays green, the hole stays documented. When the app is fixed,
the xfail turns into XPASS and the mark can go.
"""
import re
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from redteam.targets import kf_core

SET = settings(max_examples=150, deadline=None, suppress_health_check=list(HealthCheck))
KNOWN_ACCOUNT = "2400123456/2010"  # supplier 29143705 in suppliers.json


def run(patch: dict, **extra):
    return kf_core.run({"input": {"invoice": patch, **extra}})


def semantic_account(a: str):
    """Reference parser, independent of faktury.models.account_key: (prefix, number, bank) or None."""
    m = re.fullmatch(r"(?:(\d{1,6})-)?(\d{2,10})/(\d{4})", a.replace(" ", ""), flags=re.ASCII)
    if not m:
        return None
    p, n, b = m.groups()
    return (int(p or 0), int(n), b)


accounts = st.text(alphabet="0123456789-/  ​０１", min_size=1, max_size=24)


@SET
@given(accounts)
def test_changed_account_never_approves(acct):
    """A valid invoice from a known supplier with a different bank account must not be APPROVE."""
    sem = semantic_account(acct)
    if sem == semantic_account(KNOWN_ACCOUNT):
        return  # the same account written another way
    obs = run({"bank_account": acct})
    if obs["error"]:  # crash is its own property below
        return
    assert obs["decision"] != "APPROVE", acct


# --- weird numbers must never crash the core (a crash becomes HTTP 500 / MCP error) ---

WEIRD = ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity", "inf", "1E+999999", "1e-999999", "0x10",
         "1_000", "１２３", "١٢٣", "²", "", " ", "1,5", "--1", "+", ".", "1e5", "9" * 400]
FIELDS = ["qty", "unit_price", "subtotal", "vat_amount", "total", "vat_rate"]


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("val", WEIRD, ids=[f"w{i}" for i in range(len(WEIRD))])
def test_weird_number_never_crashes(field, val):
    if field in ("qty", "unit_price"):
        line = {"sku": "PAPIR-A4", "qty": 40, "unit_price": "119.00"}
        line[field] = val
        patch = {"lines": [line]}
    else:
        patch = {field: val}
    obs = run(patch)
    if obs["error"]:
        pytest.xfail(f"RT-KF-05: {field}={val!r} -> {obs['error'][:60]}")


@SET
@given(st.text(max_size=40))
def test_unicode_invoice_number_never_crashes(num):
    obs = run({"invoice_number": num})
    assert not obs["error"], (num, obs["error"])


@SET
@given(st.text(max_size=40), st.text(max_size=40))
def test_distinct_invoice_numbers_not_called_duplicates(a, b):
    """Two different invoice numbers of one supplier must not be flagged as the same invoice."""
    if a.strip() == b.strip() or not a.strip() or not b.strip():
        return
    obs = kf_core.run({"input": {"preload": [{"invoice": {"invoice_number": a}}],
                                 "invoice": {"invoice_number": b, "issue_date": "2026-10-16"}}})
    if obs["error"]:
        return
    if "DUPLICATE_NUMBER" in obs["codes"]:
        from faktury.models import number_key
        assert number_key(a) == number_key(b)
        pytest.xfail(f"RT-KF-07: {a!r} and {b!r} share key {number_key(a)!r}")


# --- arithmetic: a correct invoice must be APPROVE-able (rounding, 0 % VAT, decimal qty) ---

def q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


@SET
@given(qty=st.decimals(min_value="0.001", max_value="500", places=3),
       price=st.decimals(min_value="0.01", max_value="9999", places=2),
       rate=st.sampled_from(["0", "0.12", "0.21"]))
def test_correct_invoice_has_no_arithmetic_findings(qty, price, rate):
    """Subtotal = sum of the rounded line amounts, VAT half-up, total = sum. Rules must agree."""
    sub = q2(qty * price)
    vat = q2(sub * Decimal(rate))
    obs = run({"lines": [{"sku": "PAPIR-A4", "qty": str(qty), "unit_price": str(price)}],
               "vat_rate": rate, "subtotal": str(sub), "vat_amount": str(vat), "total": str(sub + vat),
               "po_number": None})
    assert not obs["error"], obs
    assert not {"SUBTOTAL_MISMATCH", "VAT_MISMATCH", "TOTAL_MISMATCH"} & set(obs["codes"]), obs


@SET
@given(st.lists(st.tuples(st.decimals(min_value="0.001", max_value="99", places=3),
                          st.decimals(min_value="0.01", max_value="999", places=2)), min_size=2, max_size=6))
def test_unrounded_sum_of_lines_is_accepted(lines):
    """Many suppliers sum the exact products and round once. Sum of rounded lines can differ by 0.01+."""
    exact = sum(q * p for q, p in lines)
    sub = q2(exact)
    vat = q2(sub * Decimal("0.21"))
    obs = run({"lines": [{"sku": "PAPIR-A4", "qty": str(q), "unit_price": str(p)} for q, p in lines],
               "subtotal": str(sub), "vat_amount": str(vat), "total": str(sub + vat), "po_number": None})
    if "SUBTOTAL_MISMATCH" in obs["codes"]:
        pytest.xfail("RT-KF-08: false STOP when the supplier rounds once at the end")


@SET
@given(st.integers(min_value=0, max_value=99_999_999))
def test_ico_with_leading_zeros(n):
    """IČO as number (leading zeros lost) must not crash and must not be APPROVE for an unknown supplier."""
    ico = str(n)
    obs = run({"supplier_ico": ico})
    assert not obs["error"], obs
    if ico.zfill(8) not in ("29143705",):
        assert obs["decision"] != "APPROVE", ico
