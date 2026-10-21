# RT-RAG-05: Stránka se rozbije, když server vrátí `hits: []` nebo neexistující index úseku

- **Závažnost:** Low
- **Cíl:** rag_web
- **ID útoku:** RAG-W-17, RAG-W-18 (skupina `robustness`)

## Kroky
1. Lokální web ze `site/`, `/api/ask` nahrazen odpovědí `200` se stejným tělem jako normálně, ale `hits: []` (nebo `hits: [[999999, 0.5]]`).
2. `ask()` v `site/index.html` sahá na `q.hits[0][0]` a `D.chunks[h[0]].id`, což shodí skript: `Cannot read properties of undefined (reading '0')`, odpověď se nevykreslí a uživatel vidí zamrzlou animaci.

## Očekávané
Útok je odražen: no_script_exec, no_page_error.

## Skutečné
- ok no_script_exec: no script ran
- FAIL no_page_error: page errors: ["Cannot read properties of undefined (reading '0')"]

Další útoky stejného nálezu:
- RAG-W-18: Server vrati hits s neexistujicim indexem useku → FAIL no_page_error: page errors: ['answer never rendered (page stuck)']

## Důkaz (pozorování prvního útoku)
```json
{'dialogs': [], 'pwned': False, 'injected_elements': 0, 'page_errors': ["Cannot read properties of undefined (reading '0')"], 'text': 'Zeptej se vlastními slovy, nebo vyber připravenou otázku. U připravených je změřené, jestli je odpověď správně: zelená tečka = správně, oranžová = chyba. V mapě uprostřed uvidíš, jak asistent hledá.\nJak dlouha je vypovedni doba pri vypovedi?\ndeepseek-v4-pro\n0 úseků\n\nMinimální výměra dovolené činí 4 týdny v kalendářním roce [1].\n\nživá odpověď · neověřeno\nTahle odpověď vznikla teď. Neprošla měřením ...[450 chars]'}
```

## Návrh opravy
Dnešní `ask.js` vždy vrací 5 úseků z existujícího seznamu, takže to v provozu nenastane (proto Low). Je to ale místo, kde se nedůvěřuje serveru. Oprava: v `liveAsk` před `ask()` ověřit `Array.isArray(d.hits) && d.hits.length && d.hits.every(h => D.chunks[h[0]])`, jinak ukázat chybovou hlášku.
