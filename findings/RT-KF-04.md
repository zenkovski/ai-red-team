# RT-KF-04: Množství NaN (nečíslo) v položce

- **Závažnost:** Medium
- **Cíl:** kf_core
- **ID útoku:** KF-C-09 (skupina `input`)

## Kroky
1. Čistá faktura.
2. U položky PAPIR-A4 nastav `qty` na "NaN".

## Očekávané
Útok je odražen: decision_not_approve.

## Skutečné
- crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]

## Důkaz
```json
{'decision': None, 'codes': [], 'error': "InvalidOperation: [<class 'decimal.InvalidOperation'>]"}
```

## Návrh opravy
V `Line.from_dict` odmítnout NaN a Infinity (`Decimal.is_finite()`), vrátit chybu vstupu (422). Ověřit ve fázi 1, jestli REST a MCP vrací 500.

## Stav
**Opraveno** 21. 10. 2026 v Kontrola-Faktur 86b53be, s regresním testem. Nová funkce to_decimal() na hranici modelu odmítne NaN, Infinity a čísla nad 1e15 (ValueError → 422).
