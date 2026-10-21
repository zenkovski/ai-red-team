# RT-KF-03: Cena toneru o 0,99 % vyšší než v objednávce

- **Závažnost:** Low
- **Cíl:** kf_core
- **ID útoku:** KF-C-06 (skupina `tolerance`)

## Kroky
1. Čistá faktura.
2. Toner za 1908.71 místo 1890.00 (+0,99 %), součty přepočítané.

## Očekávané
Útok je odražen: decision_not_approve.

## Skutečné
- FAIL decision_not_approve: decision=APPROVE

## Důkaz
```json
{'decision': 'APPROVE', 'codes': [], 'error': None}
```

## Návrh opravy
Známé chování (PRICE_TOLERANCE = 1 %). Možnost: tolerance v korunách na řádek (např. max 1 Kč) místo procent. Dopad: 74,84 Kč navíc projde bez upozornění; u drahých položek víc.
