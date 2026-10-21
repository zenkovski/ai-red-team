"""Shared helpers for the rag_* adapters. RAG-Demo is read-only here: we only import and run it."""
from __future__ import annotations

import os
import sys

from redteam import RAG_DIR

TOOLS = RAG_DIR / "tools"


def add_rag_to_path() -> None:
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))


def expand(v):
    """JSON attacks cannot hold a 1 MB string or NaN, so they use small markers:
    {"$repeat": ["ab", 1000]} -> "ab"*1000 ; {"$float": "nan"} ; {"$concat": [..]}."""
    if isinstance(v, dict):
        if "$repeat" in v:
            s, n = v["$repeat"]
            return s * int(n)
        if "$float" in v:
            return float(v["$float"])
        if "$concat" in v:
            return "".join(str(expand(x)) for x in v["$concat"])
        return {k: expand(x) for k, x in v.items()}
    if isinstance(v, list):
        return [expand(x) for x in v]
    return v


def offline_env() -> dict:
    """Minimal env for a RAG-Demo subprocess: offline, no API key (the key never enters this project)."""
    keep = {k: os.environ[k] for k in ("SystemRoot", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA") if k in os.environ}
    return {**keep, "RAG_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"}


def short(s, n=300) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[{len(s)} chars]"
