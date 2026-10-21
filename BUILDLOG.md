# BUILDLOG

## 2026-10-21 — plán
- Projekt naplánován, nic nepostaveno. Plán v PLAN.md, startovací prompty v START.md.
- Mapa vstupů obou aplikací sepsaná v PLAN.md (stav repozitářů k 21. 10. 2026).

## 2026-10-21 — fáze 0: kostra
- Balík `redteam/`: `run.py`, `oracles.py` (10 orákul, rozhoduje kód), `budget.py` (cache + strop 0,20 $ přes všechny běhy, `--offline`), `report.py` (vysvědčení v textu, šablona nálezu).
- Adaptér `targets/kf_core.py`: volá `faktury.pipeline.process` přímo, každý útok má vlastní prázdnou paměť (SQLite v RAM). Kód Kontroly faktur se nemění.
- 10 útoků v `redteam/attacks/kf_core.json` (kontrola, účet, DPH, strážce, tolerance, duplicity, vstup).
- Testy harnessu: 17 zelených (`python -m pytest -q`).
- Ověřeno: `python -m redteam.run --target kf_core` → **6 z 10 odraženo**, cena 0 $.
- Nálezy:
  - RT-KF-01 (Medium) DPH 50 % projde, když součty sedí.
  - RT-KF-02 (Low) strážce neodhalí anglickou parafrázi.
  - RT-KF-03 (Low, známé) cena +0,99 % projde díky toleranci 1 %.
  - RT-KF-04 (Medium) `qty = "NaN"` shodí kontrolu (InvalidOperation). Ve fázi 1 ověřit REST/MCP.
- Pozn.: Windows konzole je cp1252, `run.py` přepíná výstup na UTF-8.
- Další: fáze 1 (Sonnet). Hypothesis zatím není nainstalovaný (`pip install hypothesis`).
