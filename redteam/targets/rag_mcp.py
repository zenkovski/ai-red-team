"""RAG-Demo MCP server (tools/mcp_server.py) over real stdio, RAG_OFFLINE=1, no API key, free.

Attack input: {"tool": "get_document", "args": {...}}   (args go through rag_common.expand)
Observation: {"is_error": bool, "kind": "tool_error|protocol_error|ok", "text": str, "structured": ..., "elapsed_s": float,
              "error": None | "..."}  (error = the harness/server itself broke, counts as NOT defended)
A clean tool error or a schema rejection is a defence. A hang, a dead server or an ok result for hostile input is not.
"""
from __future__ import annotations

import asyncio
import sys
import time

from mcp import Client, StdioServerParameters

from redteam import RAG_DIR
from redteam.targets.rag_common import expand, offline_env, short

TIMEOUT_S = 60


async def _call(tool: str, args: dict) -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(RAG_DIR / "tools" / "mcp_server.py")],
                                   cwd=str(RAG_DIR), env=offline_env())
    t0 = time.perf_counter()
    async with Client(params, read_timeout_seconds=TIMEOUT_S) as client:
        try:
            r = await client.call_tool(tool, args)
        except Exception as e:  # protocol level rejection (unknown tool, invalid params) is a clean refusal
            return {"is_error": True, "kind": "protocol_error", "text": short(f"{type(e).__name__}: {e}"),
                    "structured": None, "elapsed_s": round(time.perf_counter() - t0, 3), "error": None}
        text = "\n".join(getattr(c, "text", "") or "" for c in r.content)
        return {"is_error": bool(r.is_error), "kind": "tool_error" if r.is_error else "ok", "text": text,
                "structured": r.structured_content if not r.is_error else None,
                "elapsed_s": round(time.perf_counter() - t0, 3), "error": None}


def run(attack: dict, ctx=None) -> dict:
    inp = attack["input"]
    try:
        obs = asyncio.run(asyncio.wait_for(_call(inp["tool"], expand(inp.get("args", {}))), TIMEOUT_S + 10))
    except Exception as e:
        return {"is_error": None, "text": "", "error": f"{type(e).__name__}: {short(e)}"}
    obs["text"] = short(obs["text"], 1500)
    if obs.get("structured") is not None:
        obs["structured"] = short(obs["structured"], 500)
    return obs
