"""Corre el backtest de momentum y lo compara contra benchmarks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from research.backtest_momentum import (
    backtest, buy_and_hold, equal_weight, load_prices, metrics,
)


def pct(x):
    return f"{x * 100:7.1f}%"


def row(name, m):
    return (f"  {name:22s} {pct(m['total_return']):>10} {pct(m['cagr']):>9} "
            f"{pct(m['max_drawdown']):>10} {m['sharpe']:>7.2f} {m['calmar']:>7.2f}")


if __name__ == "__main__":
    prices = load_prices(config.UNIVERSE, config.TIMEFRAME)
    print(f"Activos cargados: {list(prices.columns)}")
    print(f"Rango de datos:   {prices.index[0].date()} -> {prices.index[-1].date()}\n")

    res = backtest(
        prices,
        top_n=config.TOP_N,
        lookbacks=config.LOOKBACKS,
        rebalance_days=config.REBALANCE_DAYS,
        fee_rate=config.FEE_RATE,
        regime_symbol=config.REGIME_SYMBOL,
        regime_sma=config.REGIME_SMA,
    )
    eq = res["equity"]
    dates = eq.index

    strat_m = metrics(eq)
    bh_btc = buy_and_hold(prices, "BTC/USDT", dates)
    bh_eth = buy_and_hold(prices, "ETH/USDT", dates)
    ew = equal_weight(prices, dates)

    print("=" * 78)
    print(f"  {'ESTRATEGIA':22s} {'Total':>10} {'CAGR':>9} {'MaxDD':>10} {'Sharpe':>7} {'Calmar':>7}")
    print("-" * 78)
    print(row(f"Momentum top{config.TOP_N} +regimen", strat_m))
    print(row("Buy&Hold BTC", metrics(bh_btc)))
    print(row("Buy&Hold ETH", metrics(bh_eth)))
    print(row("Equal-Weight (todo)", metrics(ew)))
    print("=" * 78)
    print(f"\n  Periodo:            {dates[0].date()} -> {dates[-1].date()} "
          f"({(dates[-1] - dates[0]).days / 365.25:.1f} anios)")
    print(f"  Rebalanceos:        {res['n_rebalances']}")
    print(f"  Costo total fees:   {pct(res['total_fee_cost'])} del capital (acumulado)")
    print(f"  Tiempo en mercado:  {pct(res['pct_time_in_market'])} (resto en cash por regimen)")
    print(f"\n  Lectura: CAGR = retorno anual compuesto | MaxDD = peor caida desde un pico")
    print(f"           Sharpe>1 bien, >2 muy bien | Calmar = CAGR/MaxDD (cuanto ganas por unidad de dolor)")
