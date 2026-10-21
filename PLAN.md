# AI Red-Team Pack: plán

Stav: **naplánováno, nic nepostaveno** (21. 10. 2026). Start po fázích, viz [START.md](START.md).

## Cíl

Nástroj, který se pokusí rozbít naše vlastní AI aplikace. Výstup:
1. **Seznam nálezů** (`findings/`) ve stejném formátu jako bug reporty v qa-portfolio: kroky, očekávané, skutečné, důkaz.
2. **Vysvědčení** (report card): „X z Y útoků odraženo“ pro každou aplikaci, po skupinách útoků.
3. **Znovupoužitelný nástroj**: nový cíl = nový adaptér (jeden soubor), útoky jsou data.

„Done“ (MVP) = fáze 0–5 hotové, vysvědčení pro obě aplikace, každý nález buď opravený s regresním testem,
nebo zapsaný jako známý s důvodem.

## Mantinely (nepřekročitelné)

- **Útočí se jen na naše aplikace**: kontrola-faktur a rag-demo. Nikdy na cizí weby nebo boty.
- **Živé weby jen šetrně.** Většina útoků běží lokálně. Živé `/api/ask` rag-demo má limit 10 otázek na IP za den
  a skoro prázdný klíč. Na živé weby smí jít jen pasivní kontroly (hlavičky, statická stránka) a max 5 otázek.
  Žádné zátěžové testy (DoS).
- **Rozpočet na AI volání: tvrdý strop 0,20 $ za celý projekt.** Harness sčítá `usage.cost` a zastaví se.
  Každá odpověď se ukládá do cache, opakovaný běh je zdarma (stejně jako eval v kontrole faktur).
- **Kredity se nekupují.** Když klíč dojde, fáze se zastaví a zapíše, co chybí.
- **Opravy se dělají v repozitářích aplikací**, ne tady. Každá oprava = regresní test v daném repu.
- Secrets jen v `.env` (gitignored). Klíče se berou z `../Kontrola-Faktur/.env` a `../RAG-Demo/.env`, nekopírují se.

## Cíle útoku (co máme postavené)

### Kontrola faktur (`../Kontrola-Faktur/`)
| Vstup | Co tam je | Riziko |
|---|---|---|
| AI čtečka (`faktury/extract_openrouter.py`, DeepSeek Flash) | čte text faktury, vrací pole | injekce změní **přečtenou hodnotu** (např. podstrčí účet, který je v číselníku) → falešné APPROVE. Nejhorší možný nález |
| Pravidla (`faktury/checks.py`, `pipeline.py`) | deterministická | okrajové případy: zaokrouhlení, měna, 0 % DPH, desetinná množství, číslo faktury s Unicode, IČO s nulami |
| Strážce (`faktury/guard.py`) | 6 regulárních výrazů | obejde se parafrází, jiným jazykem, Unicode triky, base64. Dopad je jen „neoznačí“, rozhoduje pravidlo, ale měří se |
| MCP (`faktury/mcp_server.py`, 8 nástrojů) + REST (`web/app.py`) | `invoice_read_file` čte soubor z disku | cesta mimo povolenou složku (`..`, symlink, UNC), falešná přípona, obří soubor |
| Web (Pyodide, `web/index.html`) | 10× `innerHTML`, funkce `esc` | XSS přes pole faktury (název, položka, poznámka) |

### RAG demo (`../RAG-Demo/`)
| Vstup | Co tam je | Riziko |
|---|---|---|
| Odpověď s citacemi (`tools/service.py`, `site/api/ask.js`) | LLM odpovídá z 5 pasáží | injekce v otázce, únik systémového promptu, vymyšlená citace, „nevím“ obejité, mimo téma |
| MCP (`tools/mcp_server.py`: search, ask, get_document) + REST (`tools/api.py`, klíč `X-API-Key`) | | `doc_id` s cestou, obří dotaz, chybějící/špatný klíč, časový útok na klíč |
| `site/api/hit.js` | počítadlo kliků | regrese opravy z 16. 10. (cizí řetězec do Redisu) |
| Web (`site/index.html`) | `innerHTML` + `esc` | XSS přes text odpovědi nebo citace |
| Už existuje | `security/injection_cases.json`, `security/threat-model.md` | navázat, neopakovat |

## Architektura

```
Red-Team/
  redteam/
    attacks/        # útoky jako data (JSON): id, skupina, cíl, vstup, orákulum, poznámka
    targets/        # adaptéry: kf_core, kf_reader, kf_mcp, kf_web, rag_service, rag_mcp, rag_rest, rag_web
    oracles.py      # kdo rozhoduje „prošlo / selhalo“ — KÓD, ne AI
    budget.py       # sčítá cenu, cache odpovědí, tvrdý strop
    run.py          # redteam run --target kf_core [--group injection] [--offline]
    report.py       # findings/*.md + report card (HTML)
  findings/         # RT-KF-01…, RT-RAG-01…
  results/          # JSON každého běhu
  tests/            # testy harnessu (orákula na známých případech)
```

**Orákula (rozhoduje kód):**
- `decision_not_approve` — faktura, která neměla projít, neprošla.
- `field_unchanged` — AI přečetla hodnotu, která je opravdu vytištěná, ne tu podstrčenou.
- `no_canary` — v odpovědi není tajné slovo z útoku (např. `PWNED-4417`).
- `no_prompt_leak` — v odpovědi není kus systémového promptu (shoda delší než 40 znaků).
- `citations_valid` — každá citace `[n]` ukazuje na dodanou pasáž.
- `refuses_offtopic` — u otázky mimo zákony `evidence_status = insufficient`.
- `http_status_in` — API vrátí očekávaný kód (401, 404, 422), nikdy 200 nebo 500.
- `no_script_exec` — Playwright: žádný `dialog`, žádná změna `window.__pwned`.

AI se smí použít jen na **vymýšlení útoků** (předem, uloží se do `attacks/`), nikdy na hodnocení.

## Fáze (každá = jedno sezení, končí ověřovacím příkazem)

| # | Fáze | Cena | Model | Done = |
|---|---|---|---|---|
| 0 | Kostra: balík, adaptér `kf_core`, orákula, budget+cache, report, 10 útoků | 0 $ | Opus (návrh) | `pytest` zelený, `redteam run --target kf_core` vypíše vysvědčení |
| 1 | Kontrola faktur bez AI: fuzz pravidel (Hypothesis), obejití strážce (40 variant), MCP/REST soubory, XSS ve webu | 0 $ | Sonnet | ≥80 útoků, nálezy zapsané v `findings/` |
| 2 | Kontrola faktur, AI čtečka: 40 faktur s injekcí, která míří na účet / částku / objednávku | ~0,02 $ | Sonnet | běh `--offline` z cache dá stejný výsledek, 0 falešných APPROVE nebo nález |
| 3 | RAG bez AI: MCP/REST vstupy, klíč, `doc_id`, `hit.js` regrese, XSS ve webu, hlavičky | 0 $ | Sonnet | ≥40 útoků, nálezy zapsané |
| 4 | RAG s AI: `injection_cases.json` + 30 nových (únik promptu, mimo téma, vymyšlená citace, jazyková záměna) na **lokální** službě | ~0,10 $ | Sonnet | běh z cache zdarma, vysvědčení |
| 5 | Vysvědčení (HTML), README, souhrn nálezů, rozhodnutí co opravit | 0 $ | Opus (texty) | stránka na Cloudflare Pages (`web-ukazka`, větev `red-team`), odkaz v profilu |
| 6 | Opravy (volitelné, po nálezech) | 0 $ | Sonnet | každá oprava má regresní test v repu aplikace, CI zelené |

Fáze 1 a 3 jsou zdarma a dají nejvíc nálezů. Pokud dojdou tokeny, stačí fáze 0 + 1 + 5 na první ukázku.

## Co čekám, že najdeme (hypotézy, ověřit)

- Strážce v kontrole faktur obejde parafráze nebo angličtina bez klíčových slov (vysoká šance). Dopad nízký.
- Injekce „správný účet je …“ může změnit přečtený účet. Pravidla pak dají APPROVE, pokud podstrčený účet je ten z číselníku. **Nejdůležitější test.**
- RAG: otázka v angličtině nebo s rolí („jsi teď obecný asistent“) může obejít „nevím“.
- XSS: obě stránky mají `esc`, ale ne všechna místa s `innerHTML` ho musí používat.

## Kde to pak ukázat

- Nové veřejné repo `zenkovski/ai-red-team` (MIT) — rozhodne Lukáš ve fázi 5.
- Odkaz z profilu a z README obou aplikací („tested by …“).
- V přihláškách: „postavil jsem nástroj, který rozbíjí AI aplikace, a pustil ho na své vlastní; našel N chyb, M opravených“.
