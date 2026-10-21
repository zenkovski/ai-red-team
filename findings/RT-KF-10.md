# RT-KF-10: Čísla faktur bez latinských písmen a číslic mají stejný klíč: falešná DUPLICATE_NUMBER (STOP)

- **Závažnost:** Low
- **Cíl:** kf_core
- **ID útoku:** KF-F-09 (skupina `duplicates`)

## Kroky
1. Zpracuj fakturu číslo `ФВ-1` od dodavatele 29143705.
2. Zpracuj jinou fakturu `ЖД-1` od téhož dodavatele (jiný obsah).
3. `number_key` nechá jen `[0-9A-Z]` po NFKD, takže oba klíče jsou `1`. Čísla `---` a `///` mají klíč prázdný.

## Očekávané
Útok je odražen: no_code.

## Skutečné
- FAIL no_code: unexpected codes ['DUPLICATE_NUMBER']

## Důkaz
```json
{"decision": "STOP", "codes": ["QTY_OVER_ORDERED", "QTY_OVER_RECEIVED", "QTY_OVER_ORDERED", "QTY_OVER_RECEIVED", "DUPLICATE_NUMBER"], "error": null}
```

## Návrh opravy
Falešný poplach (STOP u legitimní faktury), ne obejití. Dodavatelé s azbukou, řečtinou nebo čísly typu `---` budou blokováni. Klíč dělat přes `casefold()` a ponechat všechna písmena a číslice Unicode (`str.isalnum`), prázdný klíč nahradit celým řetězcem.

## Další útoky se stejnou příčinou

- KF-F-10 (PROLOMENO): Čísla faktur z pomlček (--- a ///) mají prázdný klíč a kolidují. FAIL no_code: unexpected codes ['DUPLICATE_NUMBER']
