# RT-RAG-02: Strop těla 16 KB se dá obejít požadavkem po částech (chunked)

- **Závažnost:** Low
- **Cíl:** rag_rest
- **ID útoku:** RAG-R-55 (skupina `huge_input`)

## Kroky
1. `POST /api/v1/search` s platným klíčem a `Transfer-Encoding: chunked` (bez `Content-Length`), tělo `{"query": "a…a"}` o velikosti 1 MB.
2. Middleware `request_id_and_size` kontroluje jen hlavičku `Content-Length`, takže tělo projde a server ho celé načte.
3. Teprve pydantic (`max_length=500`) vrátí 422. Očekáváno bylo 413.

## Očekávané
Útok je odražen: http_status_in, text_absent.

## Skutečné
- FAIL http_status_in: status=422, allowed [413]
- ok text_absent: clean

## Důkaz (pozorování prvního útoku)
```json
{'status': 422, 'code': 'invalid_input', 'text': '{"error":{"code":"invalid_input","message":"request does not match the schema","request_id":"a27c0683065644fcb10bad996a8c55e8","details":{"fields":[{"field":"query","message":"String should have at most 500 characters"}]}}}', 'request_id': 'a27c0683065644fcb10bad996a8c55e8', 'rid_echoed': False}
```

## Návrh opravy
Dopad je malý: tělo se načte do paměti, ale nic se s ním neprovede a platný klíč je potřeba. U veřejného API bez rate limitu je to ale slabé místo pro zbytečné zatížení. Oprava: počítat bajty při čtení proudu (vlastní `receive` wrapper v ASGI middleware) nebo strop nastavit na proxy/uvicornu. Regresní test: chunked 1 MB → 413.
