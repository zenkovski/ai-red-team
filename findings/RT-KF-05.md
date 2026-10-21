# RT-KF-05: Hodnoty z AI čtečky se nevalidují: NaN, Infinity nebo přetečení shodí kontrolu (HTTP 500 / chyba MCP)

- **Závažnost:** Medium
- **Cíl:** kf_mcp
- **ID útoku:** KF-M-23 (skupina `ai-output`)

## Kroky
1. Čtečka (nebo útočník přes injekci do PDF) vrátí pole jako qty="NaN", total="NaN" nebo vat_rate="1E+999999".
2. `invoice_read_and_check` (MCP) nebo `POST /v1/read-and-check` a `POST /v1/read` (REST) výsledek zpracují.
3. Přímé `POST /v1/check` a MCP `invoice_check` stejné hodnoty odmítnou (422 / ValidationError), protože jdou přes `InvoiceIn` (ověřeno v tomto běhu). Čtecí cesta `service.check(read['invoice'])` `InvoiceIn` nepoužívá a `to_invoice` NaN propustí (Decimal('NaN') je platný).

## Očekávané
Útok je odražen: http_status_in, field_equals, decision_not_approve.

## Skutečné
- crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]

## Důkaz
```json
{"status": 500, "text": "", "elapsed_s": 0.0, "error": "InvalidOperation: [<class 'decimal.InvalidOperation'>]"}
```

## Návrh opravy
Odlišná příčina než RT-KF-04: tam padá jádro, tady padá veřejná cesta AI čtení a slib dokumentace ("když AI nepřečte, odpověď je REVIEW, nikdy chyba") neplatí. V `Line.from_dict` a `Invoice.from_dict` odmítnout nekonečná a nečíselná Decimal (`is_finite()`), v `service.read_and_check` chybu převést na REVIEW (EXTRACTION_FAILED), v `ReadOut` hodnoty validovat před odpovědí.

## Další útoky se stejnou příčinou

- KF-M-24 (PROLOMENO): AI přečetla total NaN: MCP invoice_read_and_check. crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]
- KF-M-25 (PROLOMENO): AI přečetla vat_rate 1E+999999: MCP invoice_read_and_check. crash: Overflow: [<class 'decimal.Overflow'>]
- KF-R-26 (PROLOMENO): AI přečetla qty NaN: POST /v1/read-and-check. FAIL http_status_in: status=500, allowed [200, 422]; FAIL decision_not_approve: decision=None
- KF-R-27 (PROLOMENO): AI přečetla total NaN: POST /v1/read-and-check. FAIL http_status_in: status=500, allowed [200, 422]; FAIL decision_not_approve: decision=None
- KF-R-28 (PROLOMENO): AI přečetla qty NaN: POST /v1/read (odpověď musí projít validací ReadOut). FAIL http_status_in: status=500, allowed [200, 422]
- KF-F-01 (PROLOMENO): unit_price = NaN v řádku. crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]
- KF-F-02 (PROLOMENO): qty = Infinity v řádku. crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]
- KF-F-03 (PROLOMENO): total = NaN. crash: InvalidOperation: [<class 'decimal.InvalidOperation'>]
- KF-F-04 (PROLOMENO): vat_rate = 1E+999999 (přetečení). crash: Overflow: [<class 'decimal.Overflow'>]
- KF-F-05 (PROLOMENO): subtotal = prázdný řetězec. crash: InvalidOperation: [<class 'decimal.ConversionSyntax'>]

## Stav
**Opraveno** 21. 10. 2026 v Kontrola-Faktur 86b53be, s regresním testem. Hodnoty z AI čtečky jdou přes Invoice.from_dict. /v1/read vrací 422, read-and-check REVIEW (EXTRACTION_FAILED).
