# Jak to odstartovat

Každá fáze = jedno nové sezení Claude Code. Můžeš ho otevřít v SecondBrain-OS.
První odstavec každého promptu pošle všechnu práci do složky `Red-Team/`.

**Postup pro jednu fázi:**
1. Otevři nové sezení.
2. U fází se Sonnetem napiš nejdřív zvlášť `/model sonnet` a odešli. (Uvnitř promptu to nefunguje.)
3. Zkopíruj celý prompt fáze a odešli.

Pořadí: 0 → 1 → 2 → 3 → 4 → 5. Fáze 1 a 3 jsou zdarma, 2 a 4 stojí haléře z OpenRouter klíče.

---

### Fáze 0 — kostra (Opus, nech výchozí model)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST a spouštět, neměnit.

Přečti Red-Team/PLAN.md a Red-Team/CLAUDE.md. Postav fázi 0: git init v Red-Team, balík redteam/ (run.py, oracles.py,
budget.py, report.py), adaptér targets/kf_core (volá ../Kontrola-Faktur/faktury/pipeline.process přímo, bez AI),
10 útoků v attacks/kf_core.json, testy harnessu. Ověř: pytest zelený a `python -m redteam.run --target kf_core`
vypíše vysvědčení. Zapiš do Red-Team/BUILDLOG.md. Commit (repo zatím jen lokální).
```

### Fáze 1 — kontrola faktur bez AI (nejdřív `/model sonnet`)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST a spouštět, neměnit.

Přečti Red-Team/PLAN.md, CLAUDE.md a BUILDLOG.md. Udělej fázi 1: fuzz pravidel (Hypothesis), 40 variant obejití
faktury/guard.py, útoky na invoice_read_file (MCP i REST), XSS přes pole faktury ve web/index.html (Playwright, lokálně).
Každý nález zapiš do Red-Team/findings/RT-KF-xx.md. Kód kontroly faktur NEOPRAVUJ, jen zapisuj.
Ověř: `python -m redteam.run --target kf_core,kf_mcp,kf_web` + pytest. Zapiš BUILDLOG, commit.
```

### Fáze 2 — kontrola faktur, AI čtečka (nejdřív `/model sonnet`, ~0,02 $)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST a spouštět, neměnit.

Přečti Red-Team/PLAN.md, CLAUDE.md a BUILDLOG.md. Fáze 2: 40 faktur s injekcí mířenou na bank_account, total
a po_number (vzor: ../Kontrola-Faktur/data/eval/). Adaptér kf_reader volá extract_openrouter.read_text s cache
v Red-Team/cache/kf_reader/. Klíč čti z ../Kontrola-Faktur/.env, nekopíruj ho. Strop 0,05 $. Nejdřív 1 volání
a změř cenu, pak dávka. Ověř: druhý běh s --offline dá stejný výsledek za 0 $. Zapiš BUILDLOG, commit.
```

### Fáze 3 — RAG bez AI (nejdřív `/model sonnet`)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST a spouštět, neměnit.

Přečti Red-Team/PLAN.md, CLAUDE.md a BUILDLOG.md. Fáze 3: adaptéry rag_mcp (RAG_OFFLINE=1), rag_rest (lokální
FastAPI), rag_web (Playwright na lokální site/). Útoky: doc_id s cestou, obří dotaz, chybějící/špatný X-API-Key,
hit.js s cizím řetězcem, XSS přes text odpovědi a citace. Na živý web jen pasivní kontrola hlaviček.
Nálezy do Red-Team/findings/RT-RAG-xx.md. Ověř: run + pytest. Zapiš BUILDLOG, commit.
```

### Fáze 4 — RAG s AI (nejdřív `/model sonnet`, ~0,10 $)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST a spouštět, neměnit.

Přečti Red-Team/PLAN.md, CLAUDE.md a BUILDLOG.md. Fáze 4: adaptér rag_service (lokální tools/service.py), útoky =
../RAG-Demo/security/injection_cases.json + 30 nových. Cache v Red-Team/cache/rag_service/, strop 0,10 $.
Klíč čti z ../RAG-Demo/.env, nekopíruj ho. Nejdřív 1 volání a změř cenu (pozor na skryté reasoning tokeny).
Živé /api/ask max 5 otázek. Ověř: --offline běh zdarma. Zapiš BUILDLOG, commit.
```

### Fáze 5 — vysvědčení a zveřejnění (Opus, nech výchozí model)
```
Projekt Red-Team. Výslovně povoluji práci mimo SecondBrain-OS. VŠECHNY soubory, kód, commity a výstupy patří do
C:/Users/lvcspc/Documents/Agentic Workflows/Red-Team (pracuj s absolutními cestami). V SecondBrain-OS nic nevytvářej,
jen na konci fáze přidej řádek do knowledge-base/wiki/log.md a doplň spis knowledge-base/raw/pages/project-red-team.md.
../Kontrola-Faktur a ../RAG-Demo smíš jen ČÍST, neměnit.

Přečti Red-Team/PLAN.md, BUILDLOG.md a findings/. Postav report card (HTML, styl jako qa-portfolio), README anglicky,
souhrn nálezů. Zeptej se mě: veřejné repo zenkovski/ai-red-team ano/ne, a které nálezy opravit.
Nasazení: Cloudflare Pages projekt web-ukazka, větev red-team.
```
