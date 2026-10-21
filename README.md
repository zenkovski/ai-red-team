# AI Red-Team

A small harness that attacks my own AI apps and reports what got through.
Attacks are data. Pass or fail is decided by code, never by an AI.

**Report card:** https://red-team.web-ukazka.pages.dev

## Targets

| App | What it does | Repo |
|---|---|---|
| Invoice checker | AI reads an invoice, code decides approve / review / stop | [kontrola-faktur](https://github.com/zenkovski/kontrola-faktur) |
| RAG demo | Answers from Czech labour law with citations | [rag-demo](https://github.com/zenkovski/rag-demo) |

## Results (21 Oct 2026)

| Target | Before fixes | After fixes |
|---|---|---|
| Invoice rules + injection guard (`kf_core`) | 17/64 | 24/64 |
| Invoice MCP + REST (`kf_mcp`) | 43/56 | 53/56 |
| Invoice web page, XSS (`kf_web`) | 18/20 | 18/20 |
| Invoice AI reader, injection (`kf_reader`) | 40/40 | 40/40 |
| RAG MCP server (`rag_mcp`) | 34/34 | 34/34 |
| RAG REST API + key (`rag_rest`) | 58/61 | 60/61 |
| RAG web: XSS, counter, headers (`rag_web`) | 34/41 | 34/41 * |
| RAG AI answers, local (`rag_service`) | 21/26 | 21/26 * |
| RAG live site, 5 questions (`rag_live`) | 4/5 | 4/5 * |
| **Total** | **269/347** | **288/347** |

\* Recorded before the fixes. The RAG fixes (CSP headers, citation guard) are in the repo with tests and reach these rows after deploy.

`kf_core` scores low on purpose: it holds 40 injection-guard bypass variants and fuzz cases built to find weak spots.

**23 findings, 7 Medium, 0 High. All 7 Medium are fixed** in the app repos, each with a regression test.
The rest are Low and recorded as known. See [`findings/`](findings/).

Notable:
- The AI invoice reader did **not** follow any of 40 injections, including "the correct account is …" naming the real supplier's account (19/19).
- The RAG model **did** follow an injected instruction and printed the attacker's string (RT-RAG-07). Fixed with a deterministic rule: an answer without a valid citation becomes "I don't know".
- A 50 % VAT rate passed when all sums matched (RT-KF-01). NaN quantities and broken PDFs gave HTTP 500 (RT-KF-04/05/06).

Total spent on AI calls: **0.06 $** (hard cap 0.20 $).

## How it works

```
redteam/
  attacks/   one JSON file per target: id, group, input, checks
  targets/   one adapter per target: run(attack) -> observation
  oracles.py code that decides pass/fail
  budget.py  answer cache + hard spend cap across all runs
  run.py     python -m redteam.run --target kf_core,rag_rest [--group x] [--offline]
  report.py  text report card, finding template
findings/    RT-KF-xx, RT-RAG-xx: steps, expected, actual, evidence, fix
results/     JSON of every run
site/        report card page (python site/build_site.py)
```

Oracles: `decision_not_approve`, `field_unchanged` (AI read the printed value), `no_canary`,
`no_prompt_leak`, `citations_valid`, `refuses_offtopic`, `http_status_in`, `no_script_exec` (Playwright), and a few more.
A crash is never a defence.

Every paid call goes through `budget.py`. Answers are cached, so `--offline` replays a run for 0 $.

## Run it

Needs the two target repos checked out next to this one (`../Kontrola-Faktur`, `../RAG-Demo`).

```bash
pip install pytest hypothesis playwright && python -m playwright install chromium
python -m pytest -q
python -m redteam.run --target kf_core,kf_mcp,kf_web,kf_reader,rag_mcp,rag_rest,rag_web,rag_service,rag_live --offline
```

## Limits

- One sample per attack, temperature 0. A model can behave differently next time.
- Many defended AI attacks end in "I don't know". That shows a refusal, not a good answer.
- 19 RAG attacks are marked `deferred` until the API key is topped up.
- The invoice web page was tested through its local server, not the static Pyodide build. The rendering code is the same.
- No load testing. Live sites got passive header checks and 5 questions in total.
- Built with AI (Claude Code). Attacks were designed by a human with AI; only code judges them.

## Rules

Attacks target only my own apps. Fixes live in the app repos, not here.
Secrets stay in the apps' `.env` files and are never copied.

MIT License.
