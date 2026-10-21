# RT-KF-11: Dodavatel, který sečte přesné součiny a zaokrouhlí jednou, dostane falešné SUBTOTAL_MISMATCH (STOP)

- **Závažnost:** Low
- **Cíl:** kf_core
- **ID útoku:** KF-F-11 (skupina `arithmetic`)

## Kroky
1. Řádky 0,333 x 1,01 a 0,333 x 1,01 (každý přesně 0,33633).
2. Dodavatel uvede základ 0,67 (součet přesných hodnot zaokrouhlený jednou).
3. Pravidla sčítají zaokrouhlené řádky (0,34 + 0,34 = 0,68) a hlásí STOP.

## Očekávané
Útok je odražen: no_code.

## Skutečné
- FAIL no_code: unexpected codes ['SUBTOTAL_MISMATCH']

## Důkaz
```json
{"decision": "STOP", "codes": ["SUBTOTAL_MISMATCH", "PO_MISSING"], "error": null}
```

## Návrh opravy
Hypothesis to našel jako porušenou vlastnost 'faktura sečtená s jedním zaokrouhlením nemá aritmetické nálezy'. Oprava: tolerovat rozdíl do 0,01 CZK na řádek (jako u DPH), nebo vyhodnotit oba způsoby zaokrouhlení.
