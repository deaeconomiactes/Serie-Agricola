"""Construir sólo FOB; series existentes no se leen ni se modifican."""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.magyp.cli import main

if __name__ == "__main__":
    raise SystemExit(main("build"))
