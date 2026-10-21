# RT-RAG-06: Počítadlo kliků `hit.js` se dá nafouknout podvrženým Origin (známé jako T10)

- **Závažnost:** Low
- **Cíl:** rag_web
- **ID útoku:** RAG-W-36 (skupina `hit_js`)

## Kroky
1. Spustit `site/api/hit.js` (harness ho spouští v node s falešným Redisem).
2. `POST` s hlavičkou `Origin: https://lukas-rag.vercel.app` a tělem `{"q": "<jedna z připravených otázek>"}` (kdokoli to může poslat skriptem).
3. Handler vrátí 204 a zapíše `HINCRBY` do Redisu. Kolikrát se pošle, tolikrát naroste počet.

## Očekávané
Útok je odražen: http_status_in, field_equals.

## Skutečné
- ok http_status_in: status=204, allowed [204, 403]
- FAIL field_equals: store_calls=1, expected 0

## Důkaz (pozorování prvního útoku)
```json
{'status': 204, 'ended': True, 'store_calls': 1, 'calls': [{'url': 'https://fake-redis.invalid/pipeline', 'cmds': [['HINCRBY', 'rag:preset', 'Co dostanu, když pracuji ve svátek?', 1], ['HINCRBY', 'rag:src', 'preset', 1]]}], 'error': None, 'text': '[{"url": "https://fake-redis.invalid/pipeline", "cmds": [["HINCRBY", "rag:preset", "Co dostanu, když pracuji ve svátek?", 1], ["HINCRBY", "rag:src", "preset", 1]]}]'}
```

## Návrh opravy
Zapsáno v `threat-model.md` jako T10 (zbytkové riziko, „Origin se dá podvrhnout“). Regrese opravy z 16. 10. drží: cizí řetězec se nezapíše (RAG-W-20 až W-29 a W-35 prošly), cizí Origin → 403 (W-30 až W-34). Zbývá jen nafukování počítadel připravenými otázkami; dopad je statistika, ne peníze ani data. Oprava, pokud má záležet: rate limit na IP v `hit.js` nebo počítat jen kliky s platným proof of work. Jinak nechat jako přijaté riziko.
