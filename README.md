# dca-trading-bot

Bot de inversión sistemática (DCA) sobre Binance, con alertas a Telegram y deploy
24/7 en Oracle Cloud. Filosofía: **primero no perder**.

---

## 📖 La historia (por qué DCA y no un bot "inteligente")

Antes de llegar al DCA, probamos dos estrategias activas con validación rigurosa
(walk-forward + holdout intacto):

- **Momentum rotation** → overfitting. Sharpe OOS ~0.5-0.8, drawdown -50/-60%. ❌
- **Mean-reversion** → walk-forward multi-fold 0/4 folds, Sharpe promedio OOS -0.26. ❌

**Ninguna pasó la vara** (Sharpe ≥ 1.0 y MaxDD > -35%). Conclusión: para capital de
aprendizaje, un **DCA sobre BTC** es la decisión racional, y queda como el
**benchmark que cualquier bot futuro debe vencer en OOS** para merecer plata real.
El valor del proyecto fue el *proceso*: descubrir gratis que esas estrategias no
tienen edge, en vez de perder plata averiguándolo. El código de research queda
archivado en `research/` (ver `research/README.md`).

---

## ⚙️ Cómo funciona

- **DCA (Dollar-Cost Averaging)**: compra un monto fijo de BTC cada período fijo,
  sin importar el precio. No predice nada; se sube a la tendencia de largo plazo.
- **Solo compra, nunca vende** (por diseño). Vender es decisión tuya.
- **Idempotente**: el cron lo corre todos los días, pero solo aporta 1× por período
  (mes/semana/día). Correrlo de más no duplica compras.
- **Resiliente**: si un aporte falla (red, exchange caído, sin saldo), te avisa por
  Telegram en vez de fallar en silencio.
- **3 modos** (`BOT_MODE`):
  - `simulate` — sin API keys, registra al precio público. Para arrancar.
  - `testnet` — órdenes reales en la testnet de Binance (plata **falsa**).
  - `live` — plata **real** (solo cuando decidas, Fase 3).

---

## 🚀 Setup completo paso a paso

### 0. Local (tu Mac)

```bash
git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
cd dca-trading-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # editá según los pasos siguientes
```

### 1. Telegram (alertas y reportes)

1. En Telegram, hablá con **@BotFather** → `/newbot` → copiá el **token**.
2. Mandale cualquier mensaje a tu bot nuevo (para que exista el chat).
3. Conseguí tu CHAT_ID:
   ```bash
   export TELEGRAM_BOT_TOKEN="tu-token"
   .venv/bin/python scripts/test_telegram.py     # imprime tu CHAT_ID
   ```
4. Completá en `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
5. Verificá: `.venv/bin/python scripts/test_telegram.py` → te llega "Bot conectado".

### 2. Binance Testnet (paper trading, plata falsa)

Cómo obtener las API keys de testnet (paso a paso, tal como lo hicimos):

1. Entrá a **https://testnet.binance.vision** y hacé **login con GitHub**.
2. Click en **"Generate HMAC_SHA256 Key"**.
3. **Description**: un nombre corto (ej. `Test-DCA`).
4. **Key permissions**: marcá **TRADE** (colocar órdenes) y **USER_DATA** (ver
   balance). `USER_STREAM` es opcional. *Sin TRADE, el bot no puede comprar.*
5. **Commissions/Fee**: elegí **0.1%** (no "none") para simular condiciones reales.
6. **Guardá el API Key y el Secret AHORA** — el Secret se muestra **una sola vez**.
   Si lo perdés, generás una key nueva.
7. En `.env`:
   ```
   BOT_MODE=testnet
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
8. Validá y hacé el primer aporte:
   ```bash
   set -a && . ./.env && set +a
   .venv/bin/python scripts/test_testnet.py    # ✅ conexión + balance (te da ~10.000 USDT)
   .venv/bin/python scripts/run_dca.py          # primer aporte (testnet)
   .venv/bin/python scripts/dca_status.py       # estado a Telegram
   ```

> **Notas de la testnet:**
> - Te fondea automáticamente con balances ficticios (USDT, BTC, etc.).
> - **Se resetea ~1 vez por mes** (borra balances y órdenes), pero **conserva las
>   API keys**. Tras un reset, el `portfolio_testnet.json` del bot puede quedar
>   desfasado del saldo real de testnet — es esperable, es un sandbox efímero.
> - Solo sirven los endpoints `/api` (spot). No hay retiros ni transferencias.

### 3. Deploy en Oracle Cloud (24/7 gratis)

Guía detallada: [`docs/DEPLOY_ORACLE.md`](docs/DEPLOY_ORACLE.md). Resumen:

1. **Crear la red**: Networking → VCN → *Start VCN Wizard* → "VCN with Internet
   Connectivity". Crea VCN + subnet público + internet gateway.
2. **Crear la VM**: Compute → Instances → Create:
   - Ubuntu 24.04 · Shape **VM.Standard.A1.Flex** (o **E2.1.Micro** si A1 está "out
     of capacity") · **Always Free**
   - Networking → seleccioná la VCN y el **subnet público** → activá
     **"Automatically assign public IPv4 address"**
   - SSH keys → generá y **descargá la clave privada**
3. **Conectarte y desplegar**:
   ```bash
   chmod 600 ~/Downloads/ssh-key-*.key
   ssh -i ~/Downloads/ssh-key-*.key ubuntu@TU_IP_PUBLICA
   # en la VM:
   sudo apt update && sudo apt install -y python3.12-venv git
   git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
   cd dca-trading-bot && python3 -m venv .venv && .venv/bin/pip install ccxt
   nano .env          # pegá tu .env (testnet)
   set -a && . ./.env && set +a
   .venv/bin/python scripts/test_testnet.py
   ```

### 4. Cron (que aporte solo)

En la VM, `crontab -e`:
```cron
5  9 * * *  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/run_dca.py    >> bot.log 2>&1
10 9 * * 1  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/dca_status.py >> bot.log 2>&1
```
`run_dca.py` corre diario pero solo aporta 1× por período (según `DCA_FREQUENCY`).
Horario en **UTC** (09:05 UTC = 06:05 Argentina).

### 5. Binance LIVE (plata real — Fase 3, más adelante)

Solo cuando tengas semanas de testnet andando bien:
1. En Binance (cuenta real) → API Management → crear key con permisos **solo Spot
   Trading**. **NUNCA habilites retiros (withdrawals).**
2. Restringí la key a la **IP pública de la VM** (whitelist).
3. En `.env`: `BOT_MODE=live` + las keys reales.
4. Empezá con `DCA_AMOUNT` chico.

---

## 🔧 Configuración (`.env`)

| Variable | Para qué | Default |
|---|---|---|
| `BOT_MODE` | `simulate` / `testnet` / `live` | `simulate` |
| `TELEGRAM_BOT_TOKEN` | alertas | — |
| `TELEGRAM_CHAT_ID` | alertas | — |
| `BINANCE_API_KEY` / `_SECRET` | órdenes (testnet/live) | — |
| `DCA_SYMBOL` | activo | `BTC/USDT` |
| `DCA_AMOUNT` | USDT por aporte | `50` |
| `DCA_FREQUENCY` | `monthly` / `weekly` / `daily` | `monthly` |

Fees en `src/config.py` (`FEE_RATE`): 0.1% estándar, 0.075% con BNB, 0.095% par USDC.
`.env` está en `.gitignore` — **nunca se sube a git**.

---

## 🖥️ Comandos del día a día

```bash
.venv/bin/python scripts/run_dca.py        # aporta si toca el período (idempotente)
.venv/bin/python scripts/dca_status.py     # estado + P&L + análisis de salida
.venv/bin/python scripts/dca_ledger.py     # historial completo + CSV de transacciones
.venv/bin/python scripts/dca_backtest.py   # validación histórica del DCA (fees + IRR)
.venv/bin/python tests/test_dca.py         # tests (8, sin red ni keys)
```

---

## 📂 Estructura

```
src/          config, exchange (simulate/testnet/live), portfolio, dca, notifier
scripts/      run_dca, dca_status, dca_ledger, dca_backtest, dca_demo, test_telegram, test_testnet
tests/        test_dca.py (unitarios)
research/     estrategias fallidas + harness de walk-forward (archivo, standby)
docs/         SETUP.md, DEPLOY_ORACLE.md
```

---

## 🔬 Research (standby)

Una estrategia solo gradúa a `live` si **le gana al DCA en validación OOS honesta**.
El holdout 2025-06 → 2026-06 sigue **intacto** para esa prueba. Ver `research/README.md`.

⚠️ Backtests con sesgo de supervivencia. No es asesoramiento financiero.
