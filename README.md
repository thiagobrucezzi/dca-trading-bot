# crypto-trading-bot

Bot de trading sistemático sobre Binance. Filosofía: **primero no perder**.
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

> El valor del proyecto fue el *proceso*: descubrir gratis que esas estrategias no
> tienen edge, en vez de perder plata averiguándolo.

## Estructura

```
src/                  # CÓDIGO LIVE (ejecución)
  config.py           parámetros (DCA + research)
  data_pipeline.py    descarga OHLCV de Binance (ccxt)
  exchange.py         conexión Binance — modos simulate / testnet / live
  portfolio.py        estado del portafolio (JSON por modo)
  dca.py              lógica DCA (aporte periódico idempotente)
  notifier.py         alertas Telegram
scripts/              # ENTRYPOINTS LIVE
  download_data.py    baja histórico
  run_dca.py          ejecuta el DCA (para el cron, idempotente)
  dca_status.py       reporte de estado (consola + Telegram)
  dca_demo.py         backfill histórico para demostración
  test_telegram.py    prueba/configura Telegram
research/             # ARCHIVO EN STANDBY (estrategias fallidas + harness)
  backtest_momentum.py, backtest_meanrev.py, signal.py, reporting.py
  walk_forward.py, walk_forward_mr.py, run_backtest.py, make_report.py
docs/
  DEPLOY_ORACLE.md    deploy 24/7 gratis en Oracle Cloud
```

## Uso — DCA (estrategia activa)

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # BOT_MODE=simulate para arrancar (sin keys)

.venv/bin/python scripts/run_dca.py       # aporta si toca el período
.venv/bin/python scripts/dca_status.py    # estado + P&L
.venv/bin/python scripts/dca_demo.py 18   # demo: backfill 18 meses históricos
```

**Modos** (`BOT_MODE` en `.env`): `simulate` (sin keys, arrancá acá) →
`testnet` (órdenes reales, plata falsa) → `live` (plata real, solo Fase 3).

## Uso — research (cazar un edge real, en standby)

```bash
.venv/bin/python research/walk_forward_mr.py   # validación multi-fold
.venv/bin/python research/make_report.py        # reporte HTML de un backtest
```

Una estrategia solo gradúa a `live` si **le gana al DCA en validación OOS honesta**.
El holdout 2025-06 → 2026-06 sigue **intacto** para esa prueba futura.

⚠️ Backtests con sesgo de supervivencia. No es asesoramiento financiero.
