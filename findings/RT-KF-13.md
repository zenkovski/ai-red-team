# RT-KF-13: IČO s horním indexem (²9143705) shodí `ico_valid` (isdigit() vs int())

- **Závažnost:** Low
- **Cíl:** kf_core
- **ID útoku:** KF-F-06 (skupina `input`)

## Kroky
1. `supplier_ico = "²9143705"` přes cestu AI čtení (přímé API ho vyřadí vzorem `^\d{1,8}$`).
2. `str.isdigit()` je pro '²' True, `int('²')` vyhodí ValueError.

## Očekávané
Útok je odražen: decision_not_approve.

## Skutečné
- crash: ValueError: invalid literal for int() with base 10: '²'

## Důkaz
```json
{"decision": null, "codes": [], "error": "ValueError: invalid literal for int() with base 10: '²'"}
```

## Návrh opravy
MCP výjimku chytí (vrátí chybu), REST `/v1/read-and-check` vrací 500 (KF-R-29). Použít `re.fullmatch(r'[0-9]{1,8}', ico)` místo `isdigit()`.

## Další útoky se stejnou příčinou

- KF-R-29 (PROLOMENO): AI přečetla IČO ²9143705: POST /v1/read-and-check. FAIL http_status_in: status=500, allowed [200, 422]; FAIL decision_not_approve: decision=None
