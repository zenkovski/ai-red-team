"""Every paid call goes through here: answer cache + hard spend cap.

- Same payload again -> answer from cache, 0 $.
- --offline -> cache only; a miss raises CacheMiss instead of calling the API.
- The ledger (cache/ledger.json) sums real cost across ALL runs. Over the cap -> BudgetExceeded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from redteam import CACHE_DIR

PROJECT_CAP_USD = 0.20


class BudgetExceeded(RuntimeError):
    pass


class CacheMiss(RuntimeError):
    pass


def payload_key(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


class Budget:
    def __init__(self, cap_usd: float = PROJECT_CAP_USD, root: Path | str = CACHE_DIR, offline: bool = False):
        self.cap = cap_usd
        self.root = Path(root)
        self.offline = offline
        self.ledger_path = self.root / "ledger.json"
        self.run_spent = 0.0

    @property
    def spent(self) -> float:
        if not self.ledger_path.exists():
            return 0.0
        return float(json.loads(self.ledger_path.read_text(encoding="utf-8"))["spent_usd"])

    def _add(self, cost: float) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        total = self.spent + cost
        self.ledger_path.write_text(json.dumps({"spent_usd": round(total, 6)}), encoding="utf-8")
        self.run_spent += cost

    def call(self, namespace: str, payload: dict, fn: Callable[[], tuple[dict, float]],
             estimate_usd: float = 0.0) -> dict:
        """fn() makes the real call and returns (response, cost_usd). Cached by payload."""
        path = self.root / namespace / f"{payload_key(payload)}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        if self.offline:
            raise CacheMiss(f"{namespace}/{path.name} not cached (offline run)")
        if self.spent + estimate_usd >= self.cap:
            raise BudgetExceeded(f"spent {self.spent:.4f} $ of {self.cap:.2f} $ cap")
        response, cost = fn()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"payload": payload, "response": response, "cost_usd": cost},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        self._add(float(cost))
        return response
