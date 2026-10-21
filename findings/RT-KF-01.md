# RT-KF-01: Sazba DPH 50 %, všechny součty sedí (neexistující sazba)

- **Závažnost:** Medium
- **Cíl:** kf_core
- **ID útoku:** KF-C-04 (skupina `arithmetic`)

## Kroky
1. Vezmi čistou fakturu `01-v-poradku.json`.
2. Nastav `vat_rate` 0.50, `vat_amount` 6160.00, `total` 18480.00.
3. Pošli do `faktury.pipeline.process`.

## Očekávané
Útok je odražen: decision_not_approve.

## Skutečné
- FAIL decision_not_approve: decision=APPROVE

## Důkaz
```json
{'decision': 'APPROVE', 'codes': [], 'error': None}
```

## Návrh opravy
V `checks.check_arithmetic` povolit jen platné české sazby (0, 12, 21 %). Jinou sazbu poslat na REVIEW. Regresní test v repu Kontrola-Faktur.

Dopad: doplatek 3 572,80 Kč na jedné faktuře projde bez kontroly.
