# RT-KF-09: Osamocený surrogát v čísle faktury (\ud800) shodí `POST /v1/check` na HTTP 500

- **Závažnost:** Low
- **Cíl:** kf_mcp
- **ID útoku:** KF-R-23 (skupina `rest-input`)

## Kroky
1. `POST /v1/check` s JSON `"invoice_number": "\ud800"` (platný JSON escape, neplatný Unicode).
2. Pydantic ho pustí, zápis do SQLite padne.

## Očekávané
Útok je odražen: http_status_in, text_absent.

## Skutečné
- FAIL http_status_in: status=500, allowed [200, 422]
- ok text_absent: clean

## Důkaz
```json
{"status": 500, "text": "Internal Server Error", "elapsed_s": 0.0, "error": null, "canary_seen": false}
```

## Návrh opravy
Odmítnout neplatný Unicode ve validaci (`InvoiceIn`): zakázat surrogáty a řídicí znaky v `invoice_number`, `sku`, `po_number`, `note`; nebo `encode('utf-8')` v try/except a vrátit 422.
