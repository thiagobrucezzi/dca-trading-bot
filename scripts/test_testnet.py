"""Smoke test de conectividad a la testnet de Binance.

Verifica que se puede CONECTAR y leer el mercado. La COLOCACIÓN de órdenes
requiere API keys de testnet (https://testnet.binance.vision) y se prueba
recién cuando las tengas en .env con BOT_MODE=testnet.

Uso: .venv/bin/python scripts/test_testnet.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt

from src import config


def main():
    print("1) Conectividad a testnet (sin keys, solo lectura de mercado)...")
    ex = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    ex.set_sandbox_mode(True)
    try:
        markets = ex.load_markets()
        ok = config.DCA_SYMBOL in markets
        print(f"   ✅ Conectado. {len(markets)} mercados. {config.DCA_SYMBOL} disponible: {ok}")
        t = ex.fetch_ticker(config.DCA_SYMBOL)
        print(f"   Precio testnet {config.DCA_SYMBOL}: {t['last']}")
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠️  No se pudo leer mercado de testnet: {e}")
        print("   (Puede ser red o que el endpoint público de testnet esté limitado. No es bloqueante.)")

    print("\n2) ¿Hay API keys de testnet configuradas?")
    has_keys = bool(os.environ.get("BINANCE_API_KEY") and os.environ.get("BINANCE_API_SECRET"))
    if not has_keys:
        print("   ⏳ No hay keys. Para probar órdenes reales en testnet:")
        print("      - Creá keys en https://testnet.binance.vision")
        print("      - Ponelas en .env y exportá BOT_MODE=testnet")
        print("      - Después corré: .venv/bin/python scripts/run_dca.py")
        return
    print("   ✅ Keys encontradas. Verificando balance de testnet...")
    try:
        ex.apiKey = os.environ["BINANCE_API_KEY"]
        ex.secret = os.environ["BINANCE_API_SECRET"]
        bal = ex.fetch_balance()
        usdt = bal.get("USDT", {}).get("free", 0)
        print(f"   ✅ Autenticado. USDT (testnet) disponible: {usdt}")
    except Exception as e:  # noqa: BLE001
        print(f"   ❌ Error autenticando con las keys: {e}")


if __name__ == "__main__":
    main()
