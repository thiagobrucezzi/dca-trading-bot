"""Entrypoint del DCA para el cron. Corre 1x/día; solo aporta cuando toca."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dca import run_once

if __name__ == "__main__":
    run_once()
