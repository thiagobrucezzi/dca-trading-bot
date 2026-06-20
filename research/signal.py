"""El 'cerebro': dado el historico de precios, calcula que haria el bot HOY.

Lo usan tanto el paper/live trading como el reporte diario de Telegram.
No ejecuta nada: solo decide el portafolio objetivo segun la estrategia.
"""
import pandas as pd

from research.backtest_momentum import momentum_score


def current_signal(prices, top_n=2, lookbacks=(30, 60, 90),
                   regime_symbol="BTC/USDT", regime_sma=200, asset_trend_sma=None):
    """Devuelve el estado actual de la estrategia (ultimo dato disponible)."""
    d = prices.index[-1]
    px = prices.loc[d]

    btc = prices[regime_symbol]
    sma = btc.rolling(regime_sma).mean()
    regime_on = bool(btc.loc[d] > sma.loc[d])
    btc_vs_sma = float(btc.loc[d] / sma.loc[d] - 1)

    scores = momentum_score(prices, lookbacks).loc[d].dropna().sort_values(ascending=False)

    target = pd.Series(0.0, index=prices.columns)
    picks = []
    if regime_on:
        s = scores[scores > 0]
        if asset_trend_sma:
            asma = prices.rolling(asset_trend_sma).mean().loc[d]
            s = s[[a for a in s.index if px[a] > asma[a]]]
        if len(s) > 0:
            picks = list(s.head(top_n).index)
            for a in picks:
                target[a] = 1.0 / len(picks)

    return {
        "date": d,
        "regime_on": regime_on,
        "btc_vs_sma200": btc_vs_sma,
        "ranking": [(a, float(scores[a])) for a in scores.index],
        "picks": picks,
        "target_weights": {a: float(w) for a, w in target.items() if w > 0},
        "in_cash": len(picks) == 0,
    }
