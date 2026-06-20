"""Backtest / validación del DCA sobre el histórico real de BTC.

Honra fechas de aporte (1er día de cada período) y FEES. Reporta:
  - DCA período completo y OOS (2023+): invertido, fees, valor, retorno, IRR anual
  - Comparación vs lump-sum (meter todo al inicio)
  - Dependencia de la ventana: retorno según el AÑO en que arrancaste
  - Drawdown del valor del portafolio (riesgo psicológico real)

IRR = tasa interna de retorno anualizada (retorno money-weighted, lo correcto
para aportes periódicos; un "total %" sobre lo invertido engaña porque cada
dólar estuvo invertido distinto tiempo).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src import config
from src.data_pipeline import DATA_DIR

FEE = config.FEE_RATE
AMOUNT = config.DCA_AMOUNT


def buy_dates(close, freq="monthly"):
    if freq == "weekly":
        key = [close.index.isocalendar().year, close.index.isocalendar().week]
    elif freq == "daily":
        return close
    else:
        key = [close.index.year, close.index.month]
    return close.groupby(key).head(1)


def irr_annual(monthly_cashflows):
    """Bisección sobre la tasa mensual; anualiza. cashflows: lista mensual."""
    def npv(r):
        return sum(cf / (1 + r) ** t for t, cf in enumerate(monthly_cashflows))
    lo, hi = -0.99, 1.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (1 + mid) ** 12 - 1


def dca(close, start, end, amount=AMOUNT, fee=FEE, freq="monthly"):
    s = close[(close.index >= pd.Timestamp(start, tz="UTC")) &
              (close.index <= pd.Timestamp(end, tz="UTC"))]
    buys = buy_dates(s, freq)
    units = invested = fees = 0.0
    value_curve, invested_curve = [], []
    cf = []
    # mapa fecha->precio de las compras para reconstruir unidades acumuladas
    bought = {ts: px for ts, px in buys.items()}
    cum_u = cum_i = 0.0
    for ts, px in s.items():
        if ts in bought:
            fee_amt = amount * fee
            cum_u += (amount - fee_amt) / px
            cum_i += amount
            fees += fee_amt
            cf.append(-amount)
        value_curve.append(cum_u * px)
        invested_curve.append(cum_i)
    units, invested = cum_u, cum_i
    final_value = units * s.iloc[-1]
    cf[-1] += final_value  # cobramos al final
    vc = pd.Series(value_curve, index=s.index)
    dd = float((vc / vc.cummax() - 1).min()) if len(vc) else 0.0
    return {
        "invested": invested, "fees": fees, "units": units,
        "final_value": final_value, "final_price": float(s.iloc[-1]),
        "total_return": final_value / invested - 1 if invested else 0.0,
        "irr": irr_annual(cf), "n_buys": len(buys), "max_dd": dd,
        "avg_cost": invested / units if units else 0.0,
    }


def lump_sum(close, start, end, amount, fee=FEE):
    s = close[(close.index >= pd.Timestamp(start, tz="UTC")) &
              (close.index <= pd.Timestamp(end, tz="UTC"))]
    units = (amount * (1 - fee)) / s.iloc[0]
    final = units * s.iloc[-1]
    return {"invested": amount, "final_value": final, "total_return": final / amount - 1}


def pct(x):
    return "n/a" if x is None else f"{x*100:+.1f}%"


if __name__ == "__main__":
    btc = pd.read_parquet(DATA_DIR / "BTC_USDT_1d.parquet")["close"].dropna()
    btc.index = btc.index.normalize()
    end = "2026-06-20"
    print(f"DCA sobre BTC/USDT | aporte ${AMOUNT:.0f}/mes | fee {FEE*100:.3f}% | datos hasta {end}\n")

    for label, start in [("Período completo", "2019-01-01"), ("OOS (2023+)", "2023-01-01")]:
        r = dca(btc, start, end)
        print(f"=== {label}  ({start} → {end}) ===")
        print(f"  Aportes: {r['n_buys']}  |  Invertido: ${r['invested']:,.0f}  "
              f"|  Fees totales: ${r['fees']:,.2f}")
        print(f"  Unidades: {r['units']:.4f} BTC  |  Costo promedio: ${r['avg_cost']:,.0f}")
        print(f"  Valor final: ${r['final_value']:,.0f}  (BTC a ${r['final_price']:,.0f})")
        print(f"  Retorno total s/invertido: {pct(r['total_return'])}  |  IRR anual: {pct(r['irr'])}")
        print(f"  Peor drawdown del valor: {pct(r['max_dd'])}")
        ls = lump_sum(btc, start, end, r["invested"])
        print(f"  (vs lump-sum mismo capital: {pct(ls['total_return'])} total)\n")

    print("=== Dependencia de la ventana: retorno total s/invertido según AÑO de inicio ===")
    for y in range(2019, 2026):
        r = dca(btc, f"{y}-01-01", end)
        print(f"  arranque {y}: {r['n_buys']:>2} aportes, invertido ${r['invested']:,.0f}, "
              f"retorno {pct(r['total_return']):>7}, IRR {pct(r['irr']):>7}")
    print("\n  Lección: el DCA NO garantiza ganancia en ventanas cortas/recientes;")
    print("  premia el horizonte largo y arrancar en zonas bajas (como ahora).")
