"""Configuracion central del bot. Todo lo que se toca a mano vive aca."""
import os

# --- Universo de activos a evaluar (ranking por momentum) ---
# Empezamos con majors liquidos. SOL/AVAX/etc no existian antes de ~2020,
# el pipeline baja lo que haya disponible para cada uno.
UNIVERSE = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "LINK/USDT",
]

TIMEFRAME = "1d"          # diario: ruido bajo, fees irrelevantes
START = "2019-01-01"      # incluye el bull 2020-21 y el bear 2022 (prueba de fuego)

# --- Parametros de la estrategia de momentum ---
TOP_N = 2                 # cuantos activos sostener a la vez (no todos los huevos juntos)
LOOKBACKS = (30, 60, 90)  # ventanas (dias) para medir fuerza relativa
REBALANCE_DAYS = 7        # rebalanceo semanal -> menos fees que diario
# Fees Binance Spot (volumen < 1M USD/mes). Fuente única para todo el proyecto.
#   estándar (par USDT): 0.100%  (0.001)
#   con BNB (25% off):   0.075%  (0.00075)  <- activar "pagar fees con BNB"
#   par USDC:            0.095%  (0.00095)
#   USDC + BNB:          0.071%  (0.00071)
FEE_RATE = 0.001          # default conservador (USDT estándar). Bajalo si activás BNB/USDC.
SLIPPAGE = 0.0005         # 0.05% extra por ejecucion real (fills peores que el teorico)
STOP_LOSS = 0.20          # -20% desde la entrada -> liquida la posicion a cash

# --- Particion para walk-forward (validacion a ciegas) ---
WF_SPLIT = "2023-01-01"   # train: < split | test: >= split (el modelo nunca lo vio)

# ============================================================
# DCA — estrategia activa actual (el BENCHMARK que un bot debe vencer)
# ============================================================
# Configurables por .env (sin tocar código). Default entre paréntesis.
DCA_SYMBOL = os.environ.get("DCA_SYMBOL", "BTC/USDT")
DCA_AMOUNT = float(os.environ.get("DCA_AMOUNT", "50"))        # USDT por aporte
DCA_FREQUENCY = os.environ.get("DCA_FREQUENCY", "monthly")   # monthly | weekly | daily

# --- Filtro de regimen (el "Guardian") ---
REGIME_SYMBOL = "BTC/USDT"
REGIME_SMA = 200          # si BTC < SMA200 -> mercado bajista -> a cash
