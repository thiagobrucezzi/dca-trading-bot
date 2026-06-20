"""Walk-forward MULTI-FOLD para mean-reversion + holdout final intacto.

Protocolo riguroso (anti-auto-engaño):
  - 4 folds OOS distintos (2022, 2023, 2024, 2025-H1). En cada uno se optimiza
    SOLO sobre el train (historia previa) eligiendo por Sharpe, y se valida en
    el test (que el modelo no vio). Esto evalua el PROCESO, no un config con suerte.
  - HOLDOUT final (2025-06-21 -> 2026-06-20): NO se toca durante el desarrollo.
    Solo se corre UNA vez, con la bandera --final, como prueba definitiva.

Vara de aprobacion (fijada de antemano): Sharpe >= 1.0 Y MaxDD > -35%.
"""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from research.backtest_meanrev import backtest_meanrev, load_prices
from research.backtest_momentum import metrics

BAR_SHARPE, BAR_MAXDD = 1.0, -0.35

GRID = {
    "z_window": [10, 20, 40],
    "entry_z": [1.5, 2.0, 2.5],
    "exit_z": [0.0, 0.5],
    "stop_loss": [0.10, 0.15, None],
    "use_regime": [True],          # ya probamos que False pierde plata
    "max_positions": [2, 3],
}

FOLDS = [  # (test_start, test_end); train = toda la historia previa
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
    ("2025-01-01", "2025-06-20"),
]
HOLDOUT = ("2025-06-21", "2026-06-20")


def run(prices, p, start=None, end=None):
    return backtest_meanrev(
        prices, z_window=p["z_window"], entry_z=p["entry_z"], exit_z=p["exit_z"],
        stop_loss=p["stop_loss"], use_regime=p["use_regime"],
        regime_symbol=config.REGIME_SYMBOL, regime_sma=config.REGIME_SMA,
        max_positions=p["max_positions"], fee_rate=config.FEE_RATE,
        slippage=config.SLIPPAGE, start=start, end=end,
    )


def combos():
    keys = list(GRID.keys())
    return [dict(zip(keys, v)) for v in itertools.product(*GRID.values())]


def optimize(prices, train_end):
    """Elige el mejor config por Sharpe en train (datos < train_end)."""
    best, best_sharpe = None, -1e9
    for p in combos():
        m = metrics(run(prices, p, end=train_end)["equity"])
        if m["sharpe"] > best_sharpe:
            best_sharpe, best = m["sharpe"], p
    return best, best_sharpe


def pct(x):
    return f"{x*100:6.1f}%"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--final", action="store_true", help="corre el holdout final (1 sola vez)")
    args = ap.parse_args()

    prices = load_prices(config.UNIVERSE, config.TIMEFRAME)
    print(f"Grilla: {len(combos())} configs | Folds OOS: {len(FOLDS)}\n")

    print("  === WALK-FORWARD MULTI-FOLD (optimiza train -> valida test) ===")
    print(f"  {'fold (test)':14} {'CAGR':>8} {'MaxDD':>8} {'Sharpe':>7} {'trades':>7} {'win%':>6}  config elegido")
    passes = 0
    test_sharpes, test_dds = [], []
    for ts, te in FOLDS:
        best, _ = optimize(prices, ts)
        r = run(prices, best, start=ts, end=te)
        m = metrics(r["equity"])
        test_sharpes.append(m["sharpe"])
        test_dds.append(m["max_drawdown"])
        ok = m["sharpe"] >= BAR_SHARPE and m["max_drawdown"] > BAR_MAXDD
        passes += ok
        cfg = f"z{best['z_window']} e{best['entry_z']} x{best['exit_z']} sl{best['stop_loss']} mp{best['max_positions']}"
        print(f"  {ts[:7]:14} {pct(m['cagr']):>8} {pct(m['max_drawdown']):>8} "
              f"{m['sharpe']:>7.2f} {r['n_trades']:>7} {r['win_rate']*100:>5.0f}%  {cfg} {'✅' if ok else ''}")

    avg_sharpe = sum(test_sharpes) / len(test_sharpes)
    worst_dd = min(test_dds)
    print("\n  Resumen OOS multi-fold:")
    print(f"   Sharpe promedio (folds): {avg_sharpe:.2f}")
    print(f"   Peor drawdown (folds):   {worst_dd*100:.1f}%")
    print(f"   Folds que pasan la vara: {passes}/{len(FOLDS)}")

    if not args.final:
        print("\n  (Holdout final NO ejecutado. Corre con --final cuando estemos listos para la prueba definitiva.)")
        sys.exit(0)

    print("\n  === HOLDOUT FINAL (intacto hasta ahora) ===")
    best, sh = optimize(prices, HOLDOUT[0])
    r = run(prices, best, start=HOLDOUT[0], end=HOLDOUT[1])
    m = metrics(r["equity"])
    ok = m["sharpe"] >= BAR_SHARPE and m["max_drawdown"] > BAR_MAXDD
    print(f"  Config (optim. en todo el dev): z{best['z_window']} e{best['entry_z']} "
          f"x{best['exit_z']} sl{best['stop_loss']} mp{best['max_positions']}")
    print(f"  {HOLDOUT[0]} -> {HOLDOUT[1]}")
    print(f"   CAGR {pct(m['cagr'])}  MaxDD {pct(m['max_drawdown'])}  Sharpe {m['sharpe']:.2f}  "
          f"trades {r['n_trades']}  win% {r['win_rate']*100:.0f}")
    print(f"\n   >> VEREDICTO FINAL: {'APROBADA -> Fase 2 (paper trading)' if ok else 'NO APROBADA -> vamos a Opcion B (DCA + aprender)'}")
