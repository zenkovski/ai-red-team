# RT-KF-12: Chybně zapsaný účet '-2400123456/2010' (zbytečná pomlčka) se bere jako ten známý

- **Závažnost:** Low
- **Cíl:** kf_core
- **ID útoku:** KF-F-07 (skupina `bank`)

## Kroky
1. Čistá faktura, `bank_account = "-2400123456/2010"`.
2. `account_key` rozdělí na prefix '' a číslo a vyrobí totéž co známý účet.

## Očekávané
Útok je odražen: has_code.

## Skutečné
- FAIL has_code: codes=[]

## Důkaz
```json
{"decision": "APPROVE", "codes": [], "error": null}
```

## Návrh opravy
Číslo účtu je správné, ale nevalidní zápis projde jako shodný a výsledek je APPROVE. Před porovnáním ověřit tvar `^(\d{1,6}-)?\d{2,10}/\d{4}$` a jinak hlásit REVIEW. (Zápis `00-2400123456/2010` je legitimní, ten se hlásit nemá.)
