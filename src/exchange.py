"""Conexión a Binance con 3 modos (variable de entorno BOT_MODE):

  simulate  -> NO toca el exchange. Registra el fill al precio público actual.
               No requiere API keys. Ideal para arrancar y aprender.
  testnet   -> Coloca órdenes reales en la testnet de Binance (plata FALSA).
               Requiere API keys de testnet (testnet.binance.vision).
  live      -> Plata REAL. Solo Fase 3, con autorización explícita.

El precio siempre se lee del endpoint público (no requiere keys).
"""
import os

import ccxt

from src import config

FEE_RATE = config.FEE_RATE  # fuente única en config.py (ver nota de fees BNB/USDC)


def get_mode():
    return os.environ.get("BOT_MODE", "simulate").lower()


def _public():
    return ccxt.binance({"enableRateLimit": True})


def _authed():
    ex = ccxt.binance({
        "apiKey": os.environ.get("BINANCE_API_KEY"),
        "secret": os.environ.get("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })
    if get_mode() == "testnet":
        ex.set_sandbox_mode(True)
    return ex


def get_price(symbol):
    return float(_public().fetch_ticker(symbol)["last"])


def execute_buy(symbol, quote_amount):
    """Compra `quote_amount` (USDT) de `symbol`. Devuelve el fill."""
    mode = get_mode()
    if mode == "simulate":
        price = get_price(symbol)
        fee = quote_amount * FEE_RATE
        units = (quote_amount - fee) / price
        return {"mode": mode, "symbol": symbol, "price": price,
                "units": units, "quote_spent": quote_amount, "fee": fee}

    # testnet / live: orden market real
    ex = _authed()
    price = get_price(symbol)
    units = float(ex.amount_to_precision(symbol, quote_amount / price))
    order = ex.create_market_buy_order(symbol, units)
    filled = float(order.get("filled") or units)
    avg = float(order.get("average") or price)
    cost = float(order.get("cost") or filled * avg)
    fee = float((order.get("fee") or {}).get("cost") or cost * FEE_RATE)
    return {"mode": mode, "symbol": symbol, "price": avg, "units": filled,
            "quote_spent": cost, "fee": fee, "order_id": order.get("id")}
