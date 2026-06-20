"""DEMO: backfillea aportes DCA con precios HISTÓRICOS reales de BTC.

Solo para demostración en modo simulate: muestra cómo se vería el portafolio
si hubieras venido aportando $50 al mes durante los últimos N meses.
Escribe en portfolio_simulate.json (borra el existente primero).

Uso: .venv/bin/python scripts/dca_demo.py [meses]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config
from src.exchange import FEE_RATE
from src.portfolio import DATA_DIR, Portfolio

if __name__ == "__main__":
    months = int(sys.argv[1]) if len(sys.argv) > 1 else 18

    df = pd.read_parquet(DATA_DIR / "BTC_USDT_1d.parquet")
    # primer día de cada mes
    first = df.groupby([df.index.year, df.index.month]).head(1).tail(months)

    p = DATA_DIR / "portfolio_simulate.json"
    if p.exists():
        p.unlink()
    pf = Portfolio("simulate")

    for ts, row in first.iterrows():
        price = float(row["close"])
        fee = config.DCA_AMOUNT * FEE_RATE
        units = (config.DCA_AMOUNT - fee) / price
        fill = {"mode": "simulate", "symbol": config.DCA_SYMBOL, "price": price,
                "units": units, "quote_spent": config.DCA_AMOUNT, "fee": fee}
        pf.add_buy(fill, ts.isoformat(), ts.strftime("%Y-%m"))

    print(f"Backfill demo: {len(first)} aportes de ${config.DCA_AMOUNT:.0f} "
          f"de {first.index[0].date()} a {first.index[-1].date()}")
    print("Corré 'scripts/dca_status.py' para ver el estado con precio actual.")
