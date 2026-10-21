"""Writes findings/RT-KF-05..14.md from the latest kf_* run results (python findings/_write_kf_findings.py).
Texts of steps/fix are written by hand here; the evidence (reasons, observation) comes from the run file."""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from redteam.report import finding_markdown  # noqa: E402

res = {}
for f in sorted(glob.glob(str(ROOT / "results" / "*kf_core*kf_mcp*kf_web*.json"))):
    for r in json.loads(Path(f).read_text(encoding="utf-8"))["results"]:
        res[r["id"]] = r

GUARD_HELD = (10, 13, 28, 29, 30, 31, 32)

FINDINGS = [
 ("RT-KF-05", "Medium", "Hodnoty z AI čtečky se nevalidují: NaN, Infinity nebo přetečení shodí kontrolu (HTTP 500 / chyba MCP)",
  "KF-M-23", ["KF-M-24", "KF-M-25", "KF-R-26", "KF-R-27", "KF-R-28", "KF-F-01", "KF-F-02", "KF-F-03", "KF-F-04", "KF-F-05"],
  "1. Čtečka (nebo útočník přes injekci do PDF) vrátí pole jako qty=\"NaN\", total=\"NaN\" nebo vat_rate=\"1E+999999\".\n"
  "2. `invoice_read_and_check` (MCP) nebo `POST /v1/read-and-check` a `POST /v1/read` (REST) výsledek zpracují.\n"
  "3. Přímé `POST /v1/check` a MCP `invoice_check` stejné hodnoty odmítnou (422 / ValidationError), protože jdou přes `InvoiceIn` "
  "(ověřeno v tomto běhu). Čtecí cesta `service.check(read['invoice'])` `InvoiceIn` nepoužívá a `to_invoice` NaN propustí "
  "(Decimal('NaN') je platný).",
  "Odlišná příčina než RT-KF-04: tam padá jádro, tady padá veřejná cesta AI čtení a slib dokumentace "
  "(\"když AI nepřečte, odpověď je REVIEW, nikdy chyba\") neplatí. V `Line.from_dict` a `Invoice.from_dict` odmítnout nekonečná a nečíselná "
  "Decimal (`is_finite()`), v `service.read_and_check` chybu převést na REVIEW (EXTRACTION_FAILED), v `ReadOut` hodnoty validovat před odpovědí."),
 ("RT-KF-06", "Medium", "Poškozené, prázdné nebo falešné PDF vyhodí neošetřenou výjimku (HTTP 500 / pád MCP nástroje)",
  "KF-R-19", ["KF-R-17", "KF-M-11", "KF-M-13"],
  "1. `POST /v1/read` nebo `/v1/read-and-check` s tělem `%PDF-1.4` + smetí (nebo MCP `invoice_read_file` na textový soubor pojmenovaný .pdf, "
  "nebo na prázdný .pdf).\n2. `pdf_text()` volá `fitz.open`, který vyhodí `FileDataError` / `EmptyFileError`.\n"
  "3. Služba chytá jen `ExtractionError`, `ValueError`, `PermissionError`, `FileNotFoundError`, výjimka proleze ven.",
  "V `service.read` obalit `pdf_text` do try/except a převést na `ExtractionError`. Pak `read_and_check` vrátí REVIEW (EXTRACTION_FAILED), "
  "REST 422 a MCP čistou chybu."),
 ("RT-KF-07", "Low", "Strážce (guard.py) obejde 33 ze 40 variant: parafráze, jiné jazyky, homoglyfy, kódování, rozdělení slov",
  "KF-G-02", [f"KF-G-{i:02d}" for i in range(1, 41) if i not in GUARD_HELD and i != 2] + ["KF-C-05"],
  "1. Do `raw_text` dej pokyn pro AI jinými slovy, v němčině/polštině/španělštině, s cyrilickými písmeny, base64, leetspeakem, "
  "mezerami mezi písmeny, HTML entitami, JSON/XML tagem.\n2. Zkontroluj, jestli výsledek obsahuje `TEXT_FOR_AI`.",
  "Měřeno: z 40 variant skupiny `guard` (KF-G-01..40) strážce zachytí 7 (KF-G-10, 13, 28..32: slovenské 'ignoruj', francouzské 'ignorez', "
  "zero-width a soft hyphen uvnitř slov, newline mezi slovy). Obejde 33, tedy 82,5 %. Dopad je nízký: strážce jen zvedá případ k člověku, "
  "o platbě rozhodují pravidla a AI nemá nástroje. Oprava: NFKC normalizace a mapování homoglyfů, víc jazyků, detekce base64/rot13 bloků, "
  "nebo druhý nezávislý signál (neprázdná `note` = REVIEW). Na regulární výrazy se nespoléhat jako na obranu."),
 ("RT-KF-08", "Low", "Bez limitu velikosti `document_text`: 5 MB textu zdrží strážce o 7,7 s",
  "KF-R-09", ["KF-R-10"],
  "1. `POST /api/check` s `{\"invoice\": ..., \"document_text\": \"ai \" * 1 700 000}` (5,1 MB).\n2. Změř čas odpovědi.",
  "Tělo požadavku ani `document_text` nemají strop (u `/v1/check` je to query parametr, omezený délkou URL). Strážce skenuje celý text "
  "regulárními výrazy s `.{0,40}` za každým výskytem 'ai'. Měřeno: 5,1 MB 'ai ' = 7,65 s samotný `scan_document`. Strop např. 200 kB "
  "(nad ním REVIEW bez skenování) a limit velikosti těla v reverse proxy."),
 ("RT-KF-09", "Low", "Osamocený surrogát v čísle faktury (\\ud800) shodí `POST /v1/check` na HTTP 500",
  "KF-R-23", [],
  "1. `POST /v1/check` s JSON `\"invoice_number\": \"\\ud800\"` (platný JSON escape, neplatný Unicode).\n2. Pydantic ho pustí, zápis do SQLite padne.",
  "Odmítnout neplatný Unicode ve validaci (`InvoiceIn`): zakázat surrogáty a řídicí znaky v `invoice_number`, `sku`, `po_number`, `note`; "
  "nebo `encode('utf-8')` v try/except a vrátit 422."),
 ("RT-KF-10", "Low", "Čísla faktur bez latinských písmen a číslic mají stejný klíč: falešná DUPLICATE_NUMBER (STOP)",
  "KF-F-09", ["KF-F-10"],
  "1. Zpracuj fakturu číslo `ФВ-1` od dodavatele 29143705.\n2. Zpracuj jinou fakturu `ЖД-1` od téhož dodavatele (jiný obsah).\n"
  "3. `number_key` nechá jen `[0-9A-Z]` po NFKD, takže oba klíče jsou `1`. Čísla `---` a `///` mají klíč prázdný.",
  "Falešný poplach (STOP u legitimní faktury), ne obejití. Dodavatelé s azbukou, řečtinou nebo čísly typu `---` budou blokováni. "
  "Klíč dělat přes `casefold()` a ponechat všechna písmena a číslice Unicode (`str.isalnum`), prázdný klíč nahradit celým řetězcem."),
 ("RT-KF-11", "Low", "Dodavatel, který sečte přesné součiny a zaokrouhlí jednou, dostane falešné SUBTOTAL_MISMATCH (STOP)",
  "KF-F-11", [],
  "1. Řádky 0,333 x 1,01 a 0,333 x 1,01 (každý přesně 0,33633).\n2. Dodavatel uvede základ 0,67 (součet přesných hodnot zaokrouhlený jednou).\n"
  "3. Pravidla sčítají zaokrouhlené řádky (0,34 + 0,34 = 0,68) a hlásí STOP.",
  "Hypothesis to našel jako porušenou vlastnost 'faktura sečtená s jedním zaokrouhlením nemá aritmetické nálezy'. Oprava: tolerovat rozdíl do "
  "0,01 CZK na řádek (jako u DPH), nebo vyhodnotit oba způsoby zaokrouhlení."),
 ("RT-KF-12", "Low", "Chybně zapsaný účet '-2400123456/2010' (zbytečná pomlčka) se bere jako ten známý",
  "KF-F-07", [],
  "1. Čistá faktura, `bank_account = \"-2400123456/2010\"`.\n2. `account_key` rozdělí na prefix '' a číslo a vyrobí totéž co známý účet.",
  "Číslo účtu je správné, ale nevalidní zápis projde jako shodný a výsledek je APPROVE. Před porovnáním ověřit tvar "
  "`^(\\d{1,6}-)?\\d{2,10}/\\d{4}$` a jinak hlásit REVIEW. (Zápis `00-2400123456/2010` je legitimní, ten se hlásit nemá.)"),
 ("RT-KF-13", "Low", "IČO s horním indexem (²9143705) shodí `ico_valid` (isdigit() vs int())",
  "KF-F-06", ["KF-R-29"],
  "1. `supplier_ico = \"²9143705\"` přes cestu AI čtení (přímé API ho vyřadí vzorem `^\\d{1,8}$`).\n"
  "2. `str.isdigit()` je pro '²' True, `int('²')` vyhodí ValueError.",
  "MCP výjimku chytí (vrátí chybu), REST `/v1/read-and-check` vrací 500 (KF-R-29). Použít "
  "`re.fullmatch(r'[0-9]{1,8}', ico)` místo `isdigit()`."),
 ("RT-KF-14", "Low", "Web: pole `seconds` a `image` se vkládají do innerHTML bez `esc` (hardening, skript se spustí)",
  "KF-W-19", ["KF-W-20"],
  "1. Lokální stránka (`web/index.html` přes uvicorn). Odpověď `/api/read/<id>` přepiš a vrať `seconds: \"<img src=x onerror=...>\"` "
  "nebo `image: \"x\\\" onerror=...\"`.\n"
  "2. `loaded()` skládá `za ${data.seconds} s` a `showDoc()` skládá `<img src=\"${docImage}\">` bez `esc`.",
  "Za běžného provozu jsou obě hodnoty důvěryhodné (server měří čas a staví cestu k obrázku), takže to samo není zneužitelné. "
  "Pole faktury (číslo, sku, množství, cena, poznámka, účet, IČO, datum, objednávka, název dodavatele, text dokumentu) jsou escapovaná: "
  "KF-W-02..17 odraženy, skript se nespustil. Oprava: `esc()` i u `seconds` a `docImage`, nebo `textContent`/`setAttribute`."),
]

for fid, sev, title, main, extra, steps, fix in FINDINGS:
    r = dict(res[main])
    r["title"], r["severity"] = title, sev
    obs = dict(r["observation"])
    if "text" in obs:
        obs["text"] = str(obs["text"])[:300]
    r["observation"] = json.dumps(obs, ensure_ascii=False)[:1200]
    md = finding_markdown(fid, r, steps, fix)
    if extra:
        lines = ["", "## Další útoky se stejnou příčinou", ""]
        for e in extra:
            x = res.get(e)
            if x:
                bad = "; ".join(w for w in x["reasons"] if not w.startswith("ok "))[:160]
                lines.append(f"- {e} ({'odraženo' if x['defended'] else 'PROLOMENO'}): {x['title']}. {bad}")
        md += "\n".join(lines) + "\n"
    (ROOT / "findings" / f"{fid}.md").write_text(md, encoding="utf-8")
    print(fid, sev, title[:70])
