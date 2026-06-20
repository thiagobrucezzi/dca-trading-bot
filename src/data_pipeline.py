"""Descarga y cachea historico OHLCV de Binance via ccxt.

Guarda un parquet por simbolo en data/. Idempotente: re-descarga completo
(simple y robusto para datos diarios; son pocos MB).
"""
import time
from pathlib import Path

import ccxt
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def get_exchange():
    # Solo lectura de datos publicos: no requiere API key.
    return ccxt.binance({"enableRateLimit": True})


def fetch_ohlcv_all(exchange, symbol, timeframe="1d", since_ms=None, limit=1000):
    """Pagina hacia adelante hasta agotar el historico disponible."""
    rows = []
    since = since_ms
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
        if not batch:
            break
        rows += batch
        if len(batch) < limit:
            break
        since = batch[-1][0] + 1  # ms despues de la ultima vela
        time.sleep(exchange.rateLimit / 1000)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("ts").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("date")[["open", "high", "low", "close", "volume"]]


def download(symbols, timeframe="1d", start="2019-01-01"):
    ex = get_exchange()
    since = ex.parse8601(f"{start}T00:00:00Z")
    DATA_DIR.mkdir(exist_ok=True)
    for sym in symbols:
        try:
            df = fetch_ohlcv_all(ex, sym, timeframe, since)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {sym}: error {e}")
            continue
        if df.empty:
            print(f"  ! {sym}: sin datos")
            continue
        fname = DATA_DIR / f"{sym.replace('/', '_')}_{timeframe}.parquet"
        df.to_parquet(fname)
        print(f"  ok {sym:12s} {len(df):5d} velas  {df.index[0].date()} -> {df.index[-1].date()}")
