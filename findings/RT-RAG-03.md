# RT-RAG-03: Živý web nemá Content-Security-Policy (známé jako T8, ale nezmírněné)

- **Závažnost:** Medium
- **Cíl:** rag_web
- **ID útoku:** RAG-W-37 (skupina `headers`)

## Kroky
1. `GET https://lukas-rag.vercel.app/` (jeden pasivní požadavek, odpověď uložena v `cache/rag_web_live/`).
2. V hlavičkách odpovědi chybí `Content-Security-Policy`.

## Očekávané
Útok je odražen: http_status_in, header_present.

## Skutečné
- ok http_status_in: status=200, allowed [200]
- FAIL header_present: Content-Security-Policy: None

## Důkaz (pozorování prvního útoku)
```json
{'status': 200, 'headers': {'Access-Control-Allow-Origin': '*', 'Age': '15594', 'Cache-Control': 'public, max-age=0, must-revalidate', 'Content-Disposition': 'inline', 'Content-Encoding': 'br', 'Content-Type': 'text/html; charset=utf-8', 'Date': 'Wed, 21 Oct 2026 19:08:12 GMT', 'Etag': 'W/"ad63ab531bfb67ef1bc55b1b31789bb9"', 'Last-Modified': 'Wed, 21 Oct 2026 14:48:18 GMT', 'Server': 'Vercel', 'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload', 'X-Vercel-Cache': 'HIT', 'X-Vercel-Id': 'fra1::ptcz6-1792609692569-ee9917b24889', 'Transfer-Encoding': 'chunked'}}
```

## Návrh opravy
Je to zapsané v `security/threat-model.md` (T8: „No Content-Security-Policy“). Harness potvrzuje, že stav trvá. Všech 15 XSS útoků přes odpověď/přepis/chybu proti lokálnímu webu bylo odraženo (`esc()` drží), takže CSP je teď jen druhá linie. Oprava: `vercel.json` s hlavičkou `Content-Security-Policy`. Stránka má inline skripty a načítá d3 z cdnjs a ikony z unpkg, takže nutně `script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com` (lepší: přesunout inline skripty do souboru a použít hash/nonce). Přidat `frame-ancestors 'none'`.
