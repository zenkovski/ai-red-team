# RT-RAG-01: Klíč `X-API-Key` s ne-ASCII znakem shodí REST API na HTTP 500

- **Závažnost:** Medium
- **Cíl:** rag_rest
- **ID útoku:** RAG-R-13, RAG-R-14 (skupina `auth`)

## Kroky
1. Spustit `tools/api.py` (nebo `TestClient(api.app)`), nastavit `RAG_API_KEYS=nejaky-klic`.
2. Poslat `GET /api/v1/documents/x` s hlavičkou `X-API-Key` o bajtu `0xE9` (v latin-1 „é“). Hlavička s bajty 0x80–0xFF je platné HTTP (h11 ji propustí).
3. Odpověď je `500 internal_error` a do logu jde `TypeError: comparing strings with non-ASCII characters is not supported`.
Ověřeno i na skutečném `uvicorn` (surový socket, bajt `0xE9` v hlavičce): `HTTP/1.1 500 Internal Server Error`.
Reprodukce harnessem: `python -m redteam.run --target rag_rest` (RAG-R-13, RAG-R-14).

## Očekávané
Útok je odražen: http_status_in, text_absent.

## Skutečné
- FAIL http_status_in: status=500, allowed [401]
- ok text_absent: clean

Další útoky stejného nálezu:
- RAG-R-14: Klic: klic s bajty 0xFF 0xFE → FAIL http_status_in: status=500, allowed [401]

## Důkaz (pozorování prvního útoku)
```json
{'status': 500, 'code': 'internal_error', 'text': '{"error":{"code":"internal_error","message":"unexpected server error","request_id":"2d716f9b24c14ed2a19be9dfb05847d5","details":{}}}', 'request_id': '2d716f9b24c14ed2a19be9dfb05847d5', 'rid_echoed': False}
```

## Návrh opravy
`require_key` v `tools/api.py` (řádek 101) volá `secrets.compare_digest(key, k)` na `str`. Pro `str` s ne-ASCII znaky to vyhodí `TypeError`. Oprava: porovnávat bajty, `secrets.compare_digest(key.encode("utf-8"), k.encode("utf-8"))`.
Dopad: klíč se tím neobejde (žádný přístup bez klíče), ale kdokoli bez klíče může na požádání vyrobit 500 a stack trace v logu (šum v monitoringu, falešné poplachy). Regresní test do `tests/test_api.py`: ne-ASCII klíč → 401.
