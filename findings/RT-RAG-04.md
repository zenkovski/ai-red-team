# RT-RAG-04: Živý web: chybí X-Content-Type-Options, ochrana proti iframe a Referrer-Policy

- **Závažnost:** Low
- **Cíl:** rag_web
- **ID útoku:** RAG-W-38, RAG-W-39, RAG-W-41 (skupina `headers`)

## Kroky
1. `GET https://lukas-rag.vercel.app/`.
2. V hlavičkách chybí `X-Content-Type-Options`, `X-Frame-Options` (ani `frame-ancestors` v CSP) a `Referrer-Policy`. `Strict-Transport-Security` je správně (`max-age=63072000; includeSubDomains; preload`, útok RAG-W-40 prošel).

## Očekávané
Útok je odražen: header_contains.

## Skutečné
- FAIL header_contains: X-Content-Type-Options: ''

Další útoky stejného nálezu:
- RAG-W-39: Zivy web: ochrana proti vlozeni do iframe (X-Frame-Options nebo frame-ancestors) → FAIL framing_protected: x-frame-options='', csp frame-ancestors=False
- RAG-W-41: Zivy web: Referrer-Policy → FAIL header_present: Referrer-Policy: None

## Důkaz (pozorování prvního útoku)
```json
{'status': 200, 'headers': {'Access-Control-Allow-Origin': '*', 'Age': '15594', 'Cache-Control': 'public, max-age=0, must-revalidate', 'Content-Disposition': 'inline', 'Content-Encoding': 'br', 'Content-Type': 'text/html; charset=utf-8', 'Date': 'Wed, 21 Oct 2026 19:08:12 GMT', 'Etag': 'W/"ad63ab531bfb67ef1bc55b1b31789bb9"', 'Last-Modified': 'Wed, 21 Oct 2026 14:48:18 GMT', 'Server': 'Vercel', 'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload', 'X-Vercel-Cache': 'HIT', 'X-Vercel-Id': 'fra1::ptcz6-1792609692569-ee9917b24889', 'Transfer-Encoding': 'chunked'}}
```

## Návrh opravy
`vercel.json` → `headers`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (nebo `frame-ancestors` v CSP), `Referrer-Policy: strict-origin-when-cross-origin`. Dopad: stránku může kdokoli vložit do iframe (clickjacking na živé otázky), ale web nemá přihlášení ani citlivé akce, takže je to Low.
