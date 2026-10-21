"""Merges generated attacks into kf_core.json: guard variants (KF-G-*) and fuzz findings (KF-F-*).
Idempotent: removes earlier KF-G-/KF-F- entries first. Hand-written KF-C-* attacks stay untouched."""
import json, subprocess, sys
from pathlib import Path

here = Path(__file__).parent
subprocess.run([sys.executable, str(here / "_gen_kf_guard.py")], check=True)
guard = json.loads((here / "_kf_guard_generated.json").read_text(encoding="utf-8"))

def line(qty="40", price="119.00", sku="PAPIR-A4"):
    return {"sku": sku, "qty": qty, "unit_price": price}

NO_CRASH = [{"oracle": "decision_not_approve"}]
fuzz = [
 ("KF-F-01", "input", "Medium", "unit_price = NaN v řádku", {"invoice": {"lines": [line(price="NaN")]}}, NO_CRASH),
 ("KF-F-02", "input", "Medium", "qty = Infinity v řádku", {"invoice": {"lines": [line(qty="Infinity")]}}, NO_CRASH),
 ("KF-F-03", "input", "Medium", "total = NaN", {"invoice": {"total": "NaN"}}, NO_CRASH),
 ("KF-F-04", "input", "Medium", "vat_rate = 1E+999999 (přetečení)", {"invoice": {"vat_rate": "1E+999999"}}, NO_CRASH),
 ("KF-F-05", "input", "Medium", "subtotal = prázdný řetězec", {"invoice": {"subtotal": ""}}, NO_CRASH),
 ("KF-F-06", "input", "Low", "IČO s horním indexem (²9143705) shodí isdigit/int", {"invoice": {"supplier_ico": "\u00b29143705"}}, NO_CRASH),
 ("KF-F-07", "bank", "Low", "Účet '-2400123456/2010' (zbytečná pomlčka) se bere jako ten známý",
   {"invoice": {"bank_account": "-2400123456/2010"}}, [{"oracle": "has_code", "code": "BANK_ACCOUNT_CHANGED"}]),
 ("KF-F-09", "duplicates", "Low", "Dvě různá nelatinská čísla faktur (ФВ-1 a ЖД-1) mají stejný klíč a jsou 'duplicita'",
   {"preload": [{"invoice": {"invoice_number": "ФВ-1"}}], "invoice": {"invoice_number": "ЖД-1", "issue_date": "2026-10-16"}},
   [{"oracle": "no_code", "codes": ["DUPLICATE_NUMBER"]}]),
 ("KF-F-10", "duplicates", "Low", "Čísla faktur z pomlček (--- a ///) mají prázdný klíč a kolidují",
   {"preload": [{"invoice": {"invoice_number": "---"}}], "invoice": {"invoice_number": "///", "issue_date": "2026-10-16"}},
   [{"oracle": "no_code", "codes": ["DUPLICATE_NUMBER"]}]),
 ("KF-F-11", "arithmetic", "Low", "Dodavatel sečte přesné součiny a zaokrouhlí jednou (rozdíl 0,01 proti součtu zaokrouhlených řádků)",
   {"invoice": {"lines": [line("0.333", "1.01"), line("0.333", "1.01")], "subtotal": "0.67", "vat_amount": "0.14",
                "total": "0.81", "po_number": None}},
   [{"oracle": "no_code", "codes": ["SUBTOTAL_MISMATCH", "VAT_MISMATCH", "TOTAL_MISMATCH"]}]),
 ("KF-F-12", "arithmetic", "Low", "Kontrola: 0 % DPH, správné součty, desetinné množství (nesmí hlásit aritmetiku)",
   {"invoice": {"lines": [line("2.5", "100.00")], "vat_rate": "0", "subtotal": "250.00", "vat_amount": "0.00",
                "total": "250.00", "po_number": None}},
   [{"oracle": "no_code", "codes": ["SUBTOTAL_MISMATCH", "VAT_MISMATCH", "TOTAL_MISMATCH"]}]),
 ("KF-F-13", "arithmetic", "Low", "Kontrola: půlka halíře se zaokrouhlí nahoru (0,125 -> 0,13)",
   {"invoice": {"lines": [line("1", "0.125")], "vat_rate": "0", "subtotal": "0.13", "vat_amount": "0.00",
                "total": "0.13", "po_number": None}},
   [{"oracle": "no_code", "codes": ["SUBTOTAL_MISMATCH"]}]),
 ("KF-F-14", "input", "Low", "Kontrola: IČO s IČO bez úvodní nuly (6182542) nesmí projít jako APPROVE",
   {"invoice": {"supplier_ico": "6182542"}}, NO_CRASH),
 ("KF-F-15", "input", "Low", "Číslo faktury s emoji a RTL znaky nesmí shodit kontrolu",
   {"invoice": {"invoice_number": "FV-\U0001F4A5-\u202eABC"}}, [{"oracle": "no_code", "codes": ["NEVER"]}]),
]
fz = [{"id": i, "group": g, "severity": s, "title": t, "input": inp, "checks": c} for i, g, s, t, inp, c in fuzz]

path = here / "kf_core.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["attacks"] = [a for a in data["attacks"] if not a["id"].startswith(("KF-G-", "KF-F-"))] + guard + fz
path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(data["attacks"]), "attacks in kf_core.json")
