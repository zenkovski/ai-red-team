"""python -m redteam.run --target kf_core[,kf_mcp] [--group bank] [--offline]"""
from __future__ import annotations

import argparse
import json
import sys
import time

from redteam import ATTACKS_DIR, RESULTS_DIR, targets
from redteam.budget import Budget, BudgetExceeded, CacheMiss
from redteam.oracles import judge
from redteam.report import card


def load_attacks(target: str, group: str | None = None) -> list[dict]:
    data = json.loads((ATTACKS_DIR / f"{target}.json").read_text(encoding="utf-8"))
    attacks = data["attacks"]
    # additive: attacks marked "deferred" (not run on purpose, e.g. no budget) are data only
    return [a for a in attacks if (group is None or a["group"] == group) and not a.get("deferred")]


def run_target(target: str, group: str | None, budget: Budget) -> list[dict]:
    adapter = targets.load(target)
    out = []
    for a in load_attacks(target, group):
        try:
            obs = adapter.run(a, {"budget": budget})
        except BudgetExceeded as e:
            print(f"STOP: {e}", file=sys.stderr)
            break
        except CacheMiss as e:
            obs = {"error": f"CacheMiss: {e}"}
        defended, reasons = judge(obs, a["checks"])
        out.append({"target": target, "id": a["id"], "group": a["group"], "title": a["title"],
                    "severity": a.get("severity"), "checks": a["checks"], "defended": defended,
                    "reasons": reasons, "observation": obs})
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="redteam.run")
    p.add_argument("--target", required=True, help="comma separated, e.g. kf_core,kf_mcp")
    p.add_argument("--group")
    p.add_argument("--offline", action="store_true", help="answers from cache only, 0 $")
    p.add_argument("--no-save", action="store_true")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # Windows console is cp1252, titles are Czech
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    budget = Budget(offline=args.offline)
    results = []
    for t in args.target.split(","):
        results += run_target(t.strip(), args.group, budget)

    if not args.no_save:
        RESULTS_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = RESULTS_DIR / f"{stamp}-{args.target.replace(',', '+')}.json"
        path.write_text(json.dumps({"targets": args.target, "offline": args.offline,
                                    "run_cost_usd": round(budget.run_spent, 6),
                                    "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(card(results))
    print(f"Cena behu: {budget.run_spent:.4f} $ | celkem projekt: {budget.spent:.4f} $ z {budget.cap:.2f} $")
    return 0


if __name__ == "__main__":
    sys.exit(main())
