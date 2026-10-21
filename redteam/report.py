"""Report card (text now, HTML in phase 5) and finding templates."""
from __future__ import annotations

from collections import defaultdict


def card(results: list[dict]) -> str:
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_target[r["target"]].append(r)
    out = []
    for target, rs in by_target.items():
        held = sum(r["defended"] for r in rs)
        out.append(f"VYSVEDCENI  {target}: {held} z {len(rs)} utoku odrazeno")
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in rs:
            groups[r["group"]].append(r)
        for g, gr in groups.items():
            out.append(f"  {g:<14} {sum(x['defended'] for x in gr)}/{len(gr)}")
        broken = [r for r in rs if not r["defended"]]
        if broken:
            out.append("  Prolomeno:")
            for r in broken:
                out.append(f"    {r['id']} [{r.get('severity', '?')}] {r['title']}")
                for why in r["reasons"]:
                    if not why.startswith("ok "):
                        out.append(f"        {why}")
        out.append("")
    return "\n".join(out)


def finding_markdown(fid: str, r: dict, steps: str = "", fix: str = "") -> str:
    """Skeleton in the agreed format. Steps and fix are written by a human/agent, not guessed."""
    return f"""# {fid}: {r['title']}

- **Závažnost:** {r.get('severity', '?')}
- **Cíl:** {r['target']}
- **ID útoku:** {r['id']} (skupina `{r['group']}`)

## Kroky
{steps or '1. `python -m redteam.run --target ' + r['target'] + '`'}

## Očekávané
Útok je odražen: {', '.join(c['oracle'] for c in r['checks'])}.

## Skutečné
{chr(10).join('- ' + x for x in r['reasons'])}

## Důkaz
```json
{r['observation']}
```

## Návrh opravy
{fix or '(doplnit)'}
"""
