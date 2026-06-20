"""Backtest de mean-reversion (reversion a la media) sobre cripto diario.

Idea: cuando un activo se aleja mucho hacia ABAJO de su media (z-score muy
negativo = sobrevendido), tiende a rebotar. Compramos el "dip" y salimos
cuando revierte hacia la media.

Clave para cripto: SOLO comprar dips en mercado alcista (filtro de regimen).
En un bear, los dips siguen cayendo (atrapar cuchillos) y te funden. Por eso
el filtro de regimen es protagonista, no un agregado.

Event-driven (no rebalanceo por calendario):
  - ENTRADA: activo con z < -entry_z, no tenido, regimen alcista, hay slot libre.
             Se priorizan los mas sobrevendidos.
  - SALIDA:  z >= -exit_z (revirtio) | stop-loss | timeout (max_hold dias).
  - Tamaño:  1/max_positions por slot (cash si hay menos señales que slots).

Implementado en NumPy para velocidad (el walk-forward corre cientos de veces).
"""
import numpy as np
import pandas as pd

from research.backtest_momentum import metrics, buy_and_hold, equal_weight, load_prices  # noqa: F401


def zscore(prices, window):
    ma = prices.rolling(window).mean()
    sd = prices.rolling(window).std()
    return (prices - ma) / sd


def backtest_meanrev(prices, z_window=20, entry_z=2.0, exit_z=0.5, stop_loss=0.12,
                     use_regime=True, regime_symbol="BTC/USDT", regime_sma=200,
                     max_positions=3, max_hold=20, fee_rate=0.001, slippage=0.0005,
                     start=None, end=None):
    cols = list(prices.columns)
    z = zscore(prices, z_window)
    rets = prices.pct_change().fillna(0.0)
    btc = prices[regime_symbol]
    regime_on = (btc > btc.rolling(regime_sma).mean()) if use_regime else pd.Series(True, index=prices.index)

    Pv = prices.to_numpy()
    Zv = z.to_numpy()
    Rv = rets.to_numpy()
    REGv = regime_on.to_numpy()
    idx = prices.index

    warmup = max(z_window, regime_sma if use_regime else 0)
    mask = np.zeros(len(idx), dtype=bool)
    mask[warmup:] = True
    if start is not None:
        mask &= idx >= pd.Timestamp(start, tz="UTC")
    if end is not None:
        mask &= idx <= pd.Timestamp(end, tz="UTC")
    positions = np.where(mask)[0]

    cost_rate = fee_rate + slippage
    slot_w = 1.0 / max_positions
    holdings = {}  # col_index -> [entry_price, days_held]
    eq = 1.0
    equity, exposure = [], []
    n_trades = n_stops = wins = closed = 0

    for t in positions:
        # 1) retorno del dia sobre posiciones abiertas
        if holdings:
            eq *= 1 + slot_w * sum(Rv[t, j] for j in holdings)

        # 2) salidas
        for j in list(holdings.keys()):
            h = holdings[j]
            h[1] += 1
            za = Zv[t, j]
            ret_since = Pv[t, j] / h[0] - 1
            stop_hit = stop_loss is not None and ret_since <= -stop_loss
            reverted = not np.isnan(za) and za >= -exit_z
            if stop_hit or reverted or h[1] >= max_hold:
                eq *= 1 - slot_w * cost_rate
                closed += 1
                wins += ret_since > 0
                n_stops += stop_hit
                del holdings[j]

        # 3) entradas (solo si regimen alcista y hay slots)
        if bool(REGv[t]) and len(holdings) < max_positions:
            cand = [(Zv[t, j], j) for j in range(len(cols))
                    if j not in holdings and not np.isnan(Zv[t, j]) and Zv[t, j] < -entry_z]
            cand.sort()  # mas sobrevendido (z mas bajo) primero
            for _, j in cand:
                if len(holdings) >= max_positions:
                    break
                eq *= 1 - slot_w * cost_rate
                holdings[j] = [Pv[t, j], 0]
                n_trades += 1

        equity.append(eq)
        exposure.append(len(holdings) * slot_w)

    dates = idx[positions]
    equity = pd.Series(equity, index=dates, name="strategy")
    exposure = pd.Series(exposure, index=dates, name="exposure")
    return {
        "equity": equity, "exposure": exposure,
        "n_trades": n_trades, "n_stops": n_stops,
        "win_rate": wins / closed if closed else 0.0,
        "pct_time_in_market": float((exposure > 0).mean()) if len(exposure) else 0.0,
    }
