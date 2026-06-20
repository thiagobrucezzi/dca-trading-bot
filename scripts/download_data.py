"""Baja el historico OHLCV de todo el universo y lo cachea en data/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.data_pipeline import download

if __name__ == "__main__":
    print(f"Descargando {len(config.UNIVERSE)} simbolos ({config.TIMEFRAME}) desde {config.START}...")
    download(config.UNIVERSE, config.TIMEFRAME, config.START)
    print("Listo.")
