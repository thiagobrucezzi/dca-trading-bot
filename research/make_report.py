"""Genera el reporte HTML del backtest en reports/report.html."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from research.backtest_momentum import load_prices
from research.reporting import generate

if __name__ == "__main__":
    prices = load_prices(config.UNIVERSE, config.TIMEFRAME)
    params = {
        "fee_rate": config.FEE_RATE, "slippage": config.SLIPPAGE,
        "regime_symbol": config.REGIME_SYMBOL, "regime_sma": config.REGIME_SMA,
        "top_n": config.TOP_N, "lookbacks": config.LOOKBACKS,
        "rebalance_days": config.REBALANCE_DAYS, "stop_loss": config.STOP_LOSS,
        "asset_trend_sma": None,
    }
    out, m = generate(prices, params, config.WF_SPLIT)
    print(f"Reporte generado: {out}")
    print(f"  TRAIN  Calmar {m['train']['calmar']:.2f} | Sharpe {m['train']['sharpe']:.2f}")
    print(f"  TEST   Calmar {m['test']['calmar']:.2f} | Sharpe {m['test']['sharpe']:.2f} "
          f"| MaxDD {m['test']['max_drawdown']*100:.0f}%")
    print(f"  Veredicto apto-capital: {m['verdict_ok']}")
