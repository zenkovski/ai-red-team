"""AI Red-Team Pack: attacks our own AI apps. Code decides pass/fail, never an AI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # Red-Team/
WORKSPACE = ROOT.parent                                # Agentic Workflows/
KF_DIR = WORKSPACE / "Kontrola-Faktur"
RAG_DIR = WORKSPACE / "RAG-Demo"
ATTACKS_DIR = Path(__file__).resolve().parent / "attacks"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = ROOT / "cache"
