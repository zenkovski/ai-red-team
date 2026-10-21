# Red-Team: pravidla pro agenta

Nástroj, který útočí na NAŠE AI aplikace a hledá díry. Plán: [PLAN.md](PLAN.md). Průběh: [BUILDLOG.md](BUILDLOG.md).

## Tvrdá pravidla
- Cíle jen `../Kontrola-Faktur/` a `../RAG-Demo/`. Nikdy cizí weby, boty nebo API.
- Kód cílových aplikací se v tomhle projektu NEMĚNÍ. Nálezy se jen zapisují do `findings/`. Opravy jsou samostatný krok (fáze 6) v repu aplikace.
- „Prošlo / selhalo“ rozhoduje kód (orákulum), nikdy AI.
- Každé placené volání jde přes `redteam/budget.py`: cache + tvrdý strop. Před dávkou změř cenu 1 volání.
- Živé weby: jen pasivní kontroly a max 5 otázek na `/api/ask`. Žádná zátěž.
- Secrets jen v `.env`. Klíče číst z `.env` cílových projektů, nekopírovat do kódu ani do výstupů.
- Kredity nekupovat. Když dojdou, zastavit a zapsat.

## Formát nálezu (`findings/RT-<KF|RAG>-NN.md`)
Název · závažnost (High/Medium/Low) · cíl a vstup · kroky · očekávané · skutečné · důkaz (výstup, screenshot) · ID útoku · návrh opravy.
High = vede k falešnému APPROVE, úniku tajemství nebo spuštění skriptu.

## Styl
Lidské texty česky, kód a README anglicky. Krátké věty. Čísla jen změřená.
