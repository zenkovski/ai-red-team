# RT-KF-14: Web: pole `seconds` a `image` se vkládají do innerHTML bez `esc` (hardening, skript se spustí)

- **Závažnost:** Low
- **Cíl:** kf_web
- **ID útoku:** KF-W-19 (skupina `xss`)

## Kroky
1. Lokální stránka (`web/index.html` přes uvicorn). Odpověď `/api/read/<id>` přepiš a vrať `seconds: "<img src=x onerror=...>"` nebo `image: "x\" onerror=..."`.
2. `loaded()` skládá `za ${data.seconds} s` a `showDoc()` skládá `<img src="${docImage}">` bez `esc`.

## Očekávané
Útok je odražen: field_equals, no_script_exec.

## Skutečné
- ok field_equals: form_rendered=True, expected True
- FAIL no_script_exec: dialogs=[], pwned=True

## Důkaz
```json
{"dialogs": [], "pwned": true, "page_errors": [], "form_rendered": true, "error": null}
```

## Návrh opravy
Za běžného provozu jsou obě hodnoty důvěryhodné (server měří čas a staví cestu k obrázku), takže to samo není zneužitelné. Pole faktury (číslo, sku, množství, cena, poznámka, účet, IČO, datum, objednávka, název dodavatele, text dokumentu) jsou escapovaná: KF-W-02..17 odraženy, skript se nespustil. Oprava: `esc()` i u `seconds` a `docImage`, nebo `textContent`/`setAttribute`.

## Další útoky se stejnou příčinou

- KF-W-20 (PROLOMENO): Sink bez esc: pole 'image' (src="${docImage}") rozbije atribut. FAIL no_script_exec: dialogs=[], pwned=True
