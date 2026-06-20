"""Libro mayor del DCA: historial completo + export CSV.

Muestra CADA compra con su fecha, precio y unidades, y los acumulados.
Escribe reports/dca_ledger_<modo>.csv como registro de tus transacciones.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.exchange import get_mode
from src.portfolio import Portfolio

REPORTS = Path(__file__).resolve().parent.parent / "reports"

if __name__ == "__main__":
    mode = get_mode()
    rows = Portfolio(mode).ledger()
    if not rows:
        print(f"DCA [{mode}]: sin compras registradas todavía.")
        sys.exit(0)

    print(f"LIBRO MAYOR DCA [{mode}] — {len(rows)} compras\n")
    print(f"{'fecha':11} {'período':8} {'símbolo':9} {'precio':>11} {'unidades':>11} "
          f"{'gastado':>8} {'fee':>5} | {'acum.unid':>11} {'acum.inv':>9}")
    print("-" * 100)
    cum_u = cum_i = 0.0
    for b in rows:
        cum_u += b["units"]
        cum_i += b["quote_spent"]
        print(f"{b['ts'][:10]:11} {b.get('period', ''):8} {b['symbol']:9} "
              f"{b['price']:>11,.2f} {b['units']:>11.6f} {b['quote_spent']:>8.2f} "
              f"{b.get('fee', 0):>5.2f} | {cum_u:>11.6f} {cum_i:>9,.2f}")
    print("-" * 100)
    print(f"TOTAL: {cum_u:.6f} unidades | invertido ${cum_i:,.2f} | "
          f"costo promedio ${cum_i / cum_u:,.2f}")

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"dca_ledger_{mode}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts", "period", "symbol", "price", "units", "quote_spent", "fee"])
        for b in rows:
            w.writerow([b["ts"], b.get("period", ""), b["symbol"], b["price"],
                        b["units"], b["quote_spent"], b.get("fee", 0)])
    print(f"\nCSV (registro de transacciones): {out}")
