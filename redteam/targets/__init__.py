"""Adapters. One file per target. Each exposes run(attack, ctx) -> observation dict."""
import importlib


def load(name: str):
    return importlib.import_module(f"redteam.targets.{name}")
