# RT-KF-06: Poškozené, prázdné nebo falešné PDF vyhodí neošetřenou výjimku (HTTP 500 / pád MCP nástroje)

- **Závažnost:** Medium
- **Cíl:** kf_mcp
- **ID útoku:** KF-R-19 (skupina `rest-upload`)

## Kroky
1. `POST /v1/read` nebo `/v1/read-and-check` s tělem `%PDF-1.4` + smetí (nebo MCP `invoice_read_file` na textový soubor pojmenovaný .pdf, nebo na prázdný .pdf).
2. `pdf_text()` volá `fitz.open`, který vyhodí `FileDataError` / `EmptyFileError`.
3. Služba chytá jen `ExtractionError`, `ValueError`, `PermissionError`, `FileNotFoundError`, výjimka proleze ven.

## Očekávané
Útok je odražen: http_status_in, text_absent.

## Skutečné
- FAIL http_status_in: status=500, allowed [200, 422]
- ok text_absent: clean

## Důkaz
```json
{"status": 500, "text": "Internal Server Error", "elapsed_s": 0.01, "error": null, "canary_seen": false}
```

## Návrh opravy
V `service.read` obalit `pdf_text` do try/except a převést na `ExtractionError`. Pak `read_and_check` vrátí REVIEW (EXTRACTION_FAILED), REST 422 a MCP čistou chybu.

## Další útoky se stejnou příčinou

- KF-R-17 (PROLOMENO): POST /v1/read: poškozené PDF (%PDF- a smetí). FAIL http_status_in: status=500, allowed [400, 415, 422]
- KF-M-11 (PROLOMENO): Textový soubor s příponou .pdf (falešná přípona). crash: FileDataError: Failed to open file 'C:\\Users\\lvcspc\\AppData\\Local\\Temp\\rt-kf-j671x3u0\\allowed\\fake.pdf'.
- KF-M-13 (PROLOMENO): Prázdný soubor .pdf. crash: EmptyFileError: Cannot open empty file: filename='C:\\Users\\lvcspc\\AppData\\Local\\Temp\\rt-kf-j671x3u0\\allowed\\empty.pdf'.

## Stav
**Opraveno** 21. 10. 2026 v Kontrola-Faktur 86b53be, s regresním testem. Chyba knihovny fitz se mění na ExtractionError s českou hláškou (4xx místo 500).
