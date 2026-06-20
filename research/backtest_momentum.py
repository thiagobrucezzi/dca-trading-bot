"""Backtest de rotacion por momentum con filtro de regimen, stop-loss y slippage.

Logica:
  1. Score de momentum por activo = promedio de retornos sobre varias ventanas
     (LOOKBACKS). Mide fuerza relativa.
  2. Filtro de regimen: si BTC < SMA200 -> bajista -> todo a cash.
  3. En cada rebalanceo se sostienen los TOP_N con mayor score positivo,
     equiponderados. Sin momentum positivo o regimen off -> cash.
  4. Stop-loss por posicion: si un activo cae mas de `stop_loss` desde su
     precio de entrada, se liquida a cash hasta el proximo rebalanceo.
  5. Costos: fee + slippage sobre el turnover (lo que se compra/vende).

Sin lookahead: el score/regimen en el dia D usan solo precios hasta D, y los
pesos fijados en D se aplican a los retornos de D+1 en adelante.
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_prices(symbols, timeframe="1d"):
    closes = {}
    for sym in symbols:
        f = DATA_DIR / f"{sym.replace('/', '_')}_{timeframe}.parquet"
        if not f.exists():
            continue
        closes[sym] = pd.read_parquet(f)["close"]
    prices = pd.DataFrame(closes).sort_index()
    prices.index = prices.index.normalize()
    return prices


def momentum_score(prices, lookbacks=(30, 60, 90)):
    return sum(prices.pct_change(lb) for lb in lookbacks) / len(lookbacks)


def backtest(prices, top_n=2, lookbacks=(30, 60, 90), rebalance_days=7,
             fee_rate=0.001, slippage=0.0005, regime_symbol="BTC/USDT",
             regime_sma=200, stop_loss=None, asset_trend_sma=None,
             vol_target=None, vol_lookback=20, start=None, end=None):
    """Devuelve dict con equity, exposicion y estadisticas.

    stop_loss: fraccion (ej 0.15 = -15%). None desactiva.
    asset_trend_sma: si se setea (ej 100), solo se sostiene un activo si su
        precio esta por encima de su propia SMA(N). Filtro de tendencia
        por activo: no comprar lo que esta cayendo aunque sea el "menos malo".
    vol_target: volatilidad anualizada objetivo (ej 0.40 = 40%). Si se setea,
        el peso de cada posicion se escala = base * min(1, vol_target/vol_real).
        Mercado muy volatil -> menos plata invertida, resto en cash. Sin
        apalancamiento (cap en 1). Ataca el drawdown de frente.
    start/end: recorta el periodo (str 'YYYY-MM-DD'). Para walk-forward.
    """
    rets = prices.pct_change().fillna(0.0)
    scores = momentum_score(prices, lookbacks)
    btc = prices[regime_symbol]
    sma = btc.rolling(regime_sma).mean()
    regime_on = btc > sma
    asset_sma = prices.rolling(asset_trend_sma).mean() if asset_trend_sma else None
    realized_vol = rets.rolling(vol_lookback).std() * np.sqrt(365) if vol_target else None

    warmup = max(max(lookbacks), regime_sma)
    dates = prices.index[warmup:]
    if start is not None:
        dates = dates[dates >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        dates = dates[dates <= pd.Timestamp(end, tz="UTC")]

    cols = prices.columns
    current_w = pd.Series(0.0, index=cols)
    entry_price = pd.Series(np.nan, index=cols)
    last_rebal = -10 ** 9
    eq = 1.0
    equity, exposure = [], []
    total_cost = 0.0
    n_rebalances = 0
    n_stops = 0
    cost_rate = fee_rate + slippage

    for i, d in enumerate(dates):
        # 1) retorno del dia sobre posiciones sostenidas
        eq *= 1 + float((current_w * rets.loc[d]).sum())
        px = prices.loc[d]

        # 2) stop-loss intra-periodo
        if stop_loss is not None:
            for a in list(cols[current_w > 0]):
                ep = entry_price[a]
                if not np.isnan(ep) and px[a] <= ep * (1 - stop_loss):
                    cost = float(current_w[a]) * cost_rate
                    eq *= 1 - cost
                    total_cost += cost
                    current_w[a] = 0.0
                    entry_price[a] = np.nan
                    n_stops += 1

        # 3) rebalanceo (al cierre de D, define pesos para D+1)
        if i - last_rebal >= rebalance_days:
            target = pd.Series(0.0, index=cols)
            if bool(regime_on.loc[d]):
                s = scores.loc[d].dropna()
                s = s[s > 0]
                if asset_sma is not None:  # filtro de tendencia por activo
                    above = px > asset_sma.loc[d]
                    s = s[[a for a in s.index if bool(above.get(a, False))]]
                if len(s) > 0:
                    picks = s.sort_values(ascending=False).head(top_n).index
                    base = 1.0 / len(picks)
                    for a in picks:
                        w = base
                        if vol_target is not None:
                            av = realized_vol.loc[d, a]
                            w = base * min(1.0, vol_target / av) if (not np.isnan(av) and av > 0) else 0.0
                        target[a] = w
            turnover = float((target - current_w).abs().sum())
            cost = turnover * cost_rate
            eq *= 1 - cost
            total_cost += cost
            # actualizar precios de entrada
            for a in cols:
                if target[a] > 0 and current_w[a] == 0:      # posicion nueva
                    entry_price[a] = px[a]
                elif target[a] == 0:                          # cerrada
                    entry_price[a] = np.nan
                # si sigue abierta, mantiene su entry original (stop fijo)
            current_w = target.copy()
            last_rebal = i
            n_rebalances += 1

        equity.append(eq)
        exposure.append(float(current_w.sum()))

    equity = pd.Series(equity, index=dates, name="strategy")
    exposure = pd.Series(exposure, index=dates, name="exposure")
    return {
        "equity": equity,
        "exposure": exposure,
        "total_cost": total_cost,
        "n_rebalances": n_rebalances,
        "n_stops": n_stops,
        "pct_time_in_market": float((exposure > 0).mean()) if len(exposure) else 0.0,
    }


def buy_and_hold(prices, symbol, dates):
    p = prices[symbol].reindex(dates).ffill()
    return (p / p.iloc[0]).rename(f"B&H {symbol}")


def equal_weight(prices, dates):
    rets = prices.pct_change().fillna(0.0).reindex(dates)
    return (1 + rets.mean(axis=1)).cumprod().rename("Equal-Weight")


def metrics(equity, periods_per_year=365):
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = equity.iloc[-1] / equity.iloc[0] - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    roll_max = equity.cummax()
    max_dd = float((equity / roll_max - 1).min())
    std = rets.std()
    vol = float(std * np.sqrt(periods_per_year))
    sharpe = float((rets.mean() * periods_per_year) / vol) if std > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0
    return {
        "total_return": total, "cagr": cagr, "max_drawdown": max_dd,
        "volatility": vol, "sharpe": sharpe, "calmar": calmar,
    }
