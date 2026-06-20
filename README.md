# dca-trading-bot

Bot de inversión sistemática sobre Binance. Filosofía: **primero no perder**.
El diseño parte de las razones por las que el 90% de los bots retail fracasan
(sin stop, sobre-apalancamiento, sin backtest, decisiones emocionales, hype)
y blinda contra cada una.

## Qué pasó (resumen honesto)

Probamos dos estrategias activas con validación rigurosa (walk-forward + holdout):

- **Momentum rotation** → overfitting. Sharpe OOS ~0.5-0.8, drawdown -50/-60%. ❌
- **Mean-reversion** → walk-forward multi-fold 0/4 folds, Sharpe promedio OOS -0.26. ❌

**Ninguna pasó la vara** (Sharpe ≥ 1.0 y MaxDD > -35%). Conclusión madura: para
capital de aprendizaje, **un DCA sobre BTC es la decisión racional** y queda como
el **benchmark que cualquier bot futuro debe vencer en OOS** para merecer plata real.

Validación del DCA (`scripts/dca_backtest.py`): IRR ~15-33% en horizontes largos,
pero arranques recientes (2024/2025) en rojo y drawdown del valor de hasta -74%.
El DCA premia paciencia y horizonte largo; no es magia.

> El valor del proyecto fue el *proceso*: descubrir gratis que esas estrategias no
> tienen edge, en vez de perder plata averiguándolo.

## 🚀 Empezar

**Setup completo paso a paso → [`docs/SETUP.md`](docs/SETUP.md)** (Telegram, testnet, Oracle).
**Deploy 24/7 gratis → [`docs/DEPLOY_ORACLE.md`](docs/DEPLOY_ORACLE.md).**

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # BOT_MODE=simulate para arrancar (sin keys)

.venv/bin/python scripts/run_dca.py        # aporta si toca el período (idempotente)
.venv/bin/python scripts/dca_status.py     # estado + P&L + análisis de salida
```

**Modos** (`BOT_MODE` en `.env`): `simulate` (sin keys, arrancá acá) →
`testnet` (órdenes reales, plata falsa) → `live` (plata real, solo Fase 3).

## Estructura

```
src/                  # CÓDIGO LIVE
  config.py           parámetros (DCA + fees + research)
  data_pipeline.py    descarga OHLCV de Binance (ccxt)
  exchange.py         conexión Binance — modos simulate / testnet / live
  portfolio.py        estado del portafolio + análisis de salida (JSON por modo)
  dca.py              lógica DCA (aporte periódico idempotente)
  notifier.py         alertas Telegram
scripts/              # ENTRYPOINTS
  download_data.py    baja histórico de precios
  run_dca.py          ejecuta el DCA (para el cron)
  dca_status.py       reporte de estado + análisis de salida (consola + Telegram)
  dca_ledger.py       libro mayor completo + export CSV de transacciones
  dca_backtest.py     validación histórica del DCA (fees + IRR)
  dca_demo.py         backfill histórico para demostración
  test_telegram.py    prueba/configura Telegram
  test_testnet.py     smoke test de conectividad a Binance testnet
tests/
  test_dca.py         tests unitarios (portfolio, idempotencia, fees, fills)
research/             # ARCHIVO EN STANDBY (estrategias fallidas + harness) — ver research/README.md
docs/
  SETUP.md            checklist de pasos del usuario
  DEPLOY_ORACLE.md    deploy 24/7 gratis en Oracle Cloud
```

## Tests

```bash
.venv/bin/python tests/test_dca.py          # 7 tests, sin red ni keys
.venv/bin/python scripts/dca_backtest.py    # validación histórica del DCA
```

## Research (cazar un edge real, en standby)

Una estrategia solo gradúa a `live` si **le gana al DCA en validación OOS honesta**.
El holdout 2025-06 → 2026-06 sigue **intacto** para esa prueba futura. Ver
[`research/README.md`](research/README.md).

⚠️ Backtests con sesgo de supervivencia. No es asesoramiento financiero.
