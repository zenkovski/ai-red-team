"""Build site/index.html (the report card) from the latest full run + findings/index.json.

python site/build_site.py [after.json] [--before before.json]
Default: newest full run = after; BEFORE_RUN (first full run, before fixes) = before.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEFORE_RUN = "20261021-213057-kf_core+kf_mcp+kf_web+kf_reader+rag_mcp+rag_rest+rag_web+rag_service+rag_live.json"
SITE = ROOT / "site"
# Boundary probes: built to find where a secondary layer gives up, not to break the app.
STRESS = {("kf_core", "guard"), ("kf_core", "tolerance")}

TARGETS = {
    "kf_core":     ("kontrola-faktur", "Pravidla a strážce", "Rules and injection guard"),
    "kf_mcp":      ("kontrola-faktur", "MCP a REST API", "MCP and REST API"),
    "kf_web":      ("kontrola-faktur", "Web (XSS)", "Web page (XSS)"),
    "kf_reader":   ("kontrola-faktur", "AI čtečka faktur", "AI invoice reader"),
    "rag_mcp":     ("rag-demo", "MCP server", "MCP server"),
    "rag_rest":    ("rag-demo", "REST API a klíč", "REST API and key"),
    "rag_web":     ("rag-demo", "Web (XSS, počítadlo, hlavičky)", "Web (XSS, counter, headers)"),
    "rag_service": ("rag-demo", "AI odpovědi, lokálně", "AI answers, local"),
    "rag_live":    ("rag-demo", "Živý web, 5 otázek", "Live site, 5 questions"),
}


def latest_full() -> Path:
    files = sorted(glob.glob(str(ROOT / "results" / "*.json")))
    full = [f for f in files if all(t in Path(f).name for t in TARGETS)]
    return Path((full or files)[-1])


def main() -> None:
    args = sys.argv[1:]
    before_path = ROOT / "results" / BEFORE_RUN
    if "--before" in args:
        i = args.index("--before")
        before_path = Path(args[i + 1])
        del args[i:i + 2]
    src = Path(args[0]) if args else latest_full()
    run = json.loads(src.read_text(encoding="utf-8"))
    before = defaultdict(lambda: [0, 0])
    for r in json.loads(before_path.read_text(encoding="utf-8"))["results"]:
        if (r["target"], r["group"]) in STRESS:
            continue
        before[r["target"]][0] += r["defended"]
        before[r["target"]][1] += 1
    findings = json.loads((ROOT / "findings" / "index.json").read_text(encoding="utf-8"))
    ledger = json.loads((ROOT / "cache" / "ledger.json").read_text(encoding="utf-8"))

    rows = defaultdict(lambda: {"held": 0, "total": 0, "groups": defaultdict(lambda: [0, 0])})
    stress = defaultdict(lambda: [0, 0])
    for r in run["results"]:
        if (r["target"], r["group"]) in STRESS:
            stress[r["group"]][0] += r["defended"]
            stress[r["group"]][1] += 1
            continue
        t = rows[r["target"]]
        t["total"] += 1
        t["held"] += r["defended"]
        g = t["groups"][r["group"]]
        g[1] += 1
        g[0] += r["defended"]
    targets = []
    for key, (app, cs, en) in TARGETS.items():
        if key in rows:
            t = rows[key]
            targets.append({"key": key, "app": app, "cs": cs, "en": en, "held": t["held"], "total": t["total"],
                            "before": before[key][0],
                            "groups": [[g, v[0], v[1]] for g, v in t["groups"].items()]})

    data = {
        "date": src.name[:8],
        "targets": targets,
        "findings": findings,
        "cost": round(ledger["spent_usd"], 3),
        "attacks": sum(t["total"] for t in targets),
        "held": sum(t["held"] for t in targets),
        "before": sum(t["before"] for t in targets),
        "stress": {g: v for g, v in stress.items()},
        "reader": [rows["kf_reader"]["held"], rows["kf_reader"]["total"]],
    }
    html = (SITE / "template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (SITE / "index.html").write_text(html, encoding="utf-8")
    print(f"site/index.html: {data['held']}/{data['attacks']} real attacks held, stress {dict(stress)}, {len(findings)} findings, from {src.name}")


if __name__ == "__main__":
    main()
