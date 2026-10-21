# RT-KF-08: Bez limitu velikosti `document_text`: 5 MB textu zdrží strážce o 7,7 s

- **Závažnost:** Low
- **Cíl:** kf_mcp
- **ID útoku:** KF-R-09 (skupina `dos`)

## Kroky
1. `POST /api/check` s `{"invoice": ..., "document_text": "ai " * 1 700 000}` (5,1 MB).
2. Změř čas odpovědi.

## Očekávané
Útok je odražen: http_status_in, elapsed_below.

## Skutečné
- ok http_status_in: status=200, allowed [200, 413, 422]
- FAIL elapsed_below: elapsed=8.32s, limit 5s

## Důkaz
```json
{"status": 200, "text": "{\"decision\":\"REVIEW\",\"replay\":false,\"invoice_id\":4,\"steps\":[{\"key\":\"ico\",\"label\":\"IČO dodavatele\",\"status\":\"OK\",\"findings\":[]},{\"key\":\"math\",\"label\":\"Součty a DPH\",\"status\":\"OK\",\"findings\":[]},{\"key\":\"supplier\",\"label\":\"Dodavatel a bankovní účet\",\"status\":\"OK\",\"findings\":[]},{\"key\":\"match\",\"label\":\"", "elapsed_s": 8.32, "error": null, "canary_seen": false, "has_error_key": false, "decision": "REVIEW", "codes": ["QTY_OVER_ORDERED", "QTY_OVER_RECEIVED", "QTY_OVER_ORDERED", "QTY_OVER_RECEIVED", "POSSIBLE_DUPLICATE"]}
```

## Návrh opravy
Tělo požadavku ani `document_text` nemají strop (u `/v1/check` je to query parametr, omezený délkou URL). Strážce skenuje celý text regulárními výrazy s `.{0,40}` za každým výskytem 'ai'. Měřeno: 5,1 MB 'ai ' = 7,65 s samotný `scan_document`. Strop např. 200 kB (nad ním REVIEW bez skenování) a limit velikosti těla v reverse proxy.

## Další útoky se stejnou příčinou

- KF-R-10 (odraženo): POST /api/check: document_text 5 MB ('pokyn ' opakovaně). 
