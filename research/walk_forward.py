"""Walk-forward / out-of-sample.

La trampa del backtest comun: optimizar parametros sobre TODO el historico
y mostrar el resultado. Eso es hacer trampa (overfitting): el modelo ya "vio"
el futuro. Aca hacemos lo honesto:

  1. TRAIN  (datos viejos, < WF_SPLIT): probamos una grilla de parametros y
     elegimos el mejor por Calmar (retorno / dolor).
  2. TEST   (datos nuevos, >= WF_SPLIT): corremos ESE config una sola vez,
     sobre datos que nunca se usaron para elegir. Si aca tambien funciona,
     hay evidencia de que la estrategia es real y no un espejismo del pasado.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from research.backtest_momentum import backtest, load_prices, metrics


def pct(x):
    return f"{x * 100:6.1f}%"


# Grilla de parametros a explorar en TRAIN
GRID = {
    "top_n": [1, 2, 3],
    "lookbacks": [(30, 60, 90), (20, 50), (60, 120)],
    "rebalance_days": [7, 14],
    "stop_loss": [None, 0.20],
    "asset_trend_sma": [None, 100],
    "vol_target": [None, 0.40, 0.60],
}


def run(prices, params, start=None, end=None):
    return backtest(
        prices, top_n=params["top_n"], lookbacks=params["lookbacks"],
        rebalance_days=params["rebalance_days"], fee_rate=config.FEE_RATE,
        slippage=config.SLIPPAGE, regime_symbol=config.REGIME_SYMBOL,
        regime_sma=config.REGIME_SMA, stop_loss=params["stop_loss"],
        asset_trend_sma=params["asset_trend_sma"], vol_target=params["vol_target"],
        start=start, end=end,
    )


if __name__ == "__main__":
    prices = load_prices(config.UNIVERSE, config.TIMEFRAME)
    split = config.WF_SPLIT
    print(f"Walk-forward  |  TRAIN < {split} <= TEST\n")

    keys = list(GRID.keys())
    combos = [dict(zip(keys, vals)) for vals in itertools.product(*GRID.values())]
    print(f"Evaluando {len(combos)} combinaciones en TRAIN (eligiendo por Calmar)...\n")

    scored = []
    for p in combos:
        res = run(prices, p, end=split)
        m = metrics(res["equity"])
        scored.append((m["calmar"], m, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    print("  Top 5 configs en TRAIN:")
    print(f"  {'rank':>4} {'CAGR':>8} {'MaxDD':>8} {'Sharpe':>7} {'Calmar':>7}  parametros")
    for rank, (cal, m, p) in enumerate(scored[:5], 1):
        cfg = (f"top{p['top_n']} lb{p['lookbacks']} rb{p['rebalance_days']} "
               f"sl{p['stop_loss']} trend{p['asset_trend_sma']} vt{p['vol_target']}")
        print(f"  {rank:>4} {pct(m['cagr']):>8} {pct(m['max_drawdown']):>8} "
              f"{m['sharpe']:>7.2f} {m['calmar']:>7.2f}  {cfg}")

    best = scored[0][2]
    print(f"\n  >> Config elegida en TRAIN: {best}\n")

    # Validacion a ciegas en TEST
    tr = metrics(run(prices, best, end=split)["equity"])
    te_res = run(prices, best, start=split)
    te = metrics(te_res["equity"])

    print("=" * 60)
    print(f"  {'':10} {'CAGR':>9} {'MaxDD':>9} {'Sharpe':>8} {'Calmar':>8}")
    print("-" * 60)
    print(f"  {'TRAIN':10} {pct(tr['cagr']):>9} {pct(tr['max_drawdown']):>9} "
          f"{tr['sharpe']:>8.2f} {tr['calmar']:>8.2f}")
    print(f"  {'TEST(OOS)':10} {pct(te['cagr']):>9} {pct(te['max_drawdown']):>9} "
          f"{te['sharpe']:>8.2f} {te['calmar']:>8.2f}")
    print("=" * 60)
    print(f"\n  TEST: {te_res['n_rebalances']} rebalanceos, {te_res['n_stops']} stop-loss "
          f"disparados, {pct(te_res['pct_time_in_market'])} en mercado")

    # Vara de aprobacion fijada de antemano (no se toca despues de ver el resultado)
    BAR_SHARPE, BAR_MAXDD = 1.0, -0.35
    pass_sharpe = te["sharpe"] >= BAR_SHARPE
    pass_dd = te["max_drawdown"] > BAR_MAXDD
    approved = pass_sharpe and pass_dd
    print("\n  === VARA DE APROBACION (fijada antes de mirar) ===")
    print(f"   Sharpe >= {BAR_SHARPE:.1f} : {te['sharpe']:.2f}  {'PASA' if pass_sharpe else 'NO PASA'}")
    print(f"   MaxDD  > {BAR_MAXDD*100:.0f}%  : {te['max_drawdown']*100:.1f}%  {'PASA' if pass_dd else 'NO PASA'}")
    print(f"\n   >> VEREDICTO: {'APROBADA -> lista para paper trading (Fase 2)' if approved else 'NO APROBADA -> no se arriesga capital'}")
