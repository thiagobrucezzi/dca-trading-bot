# SETUP — Pasos de TU lado (checklist)

Esto es lo que tenés que completar vos. El código ya está listo y testeado.
Orden recomendado: **Telegram → testnet → Oracle → (más adelante) live**.

---

## 0. Resumen de lo que falta (tu lado)

- [ ] Crear el bot de **Telegram** y pegar token + chat_id en `.env`
- [ ] Crear **API keys de testnet** de Binance y pegarlas en `.env`
- [ ] Crear la **VM en Oracle** (ver `docs/DEPLOY_ORACLE.md`)
- [ ] (Opcional) **Push a GitHub** en tu cuenta personal
- [ ] (Fase 3, más adelante) API keys **reales** de Binance

Nada de esto toca plata real hasta la Fase 3.

---

## 1. Telegram (5 minutos)

1. En Telegram, hablá con **@BotFather** → `/newbot` → seguí los pasos → copiá el **token**.
2. Mandale **cualquier mensaje** a tu bot nuevo (para que exista el chat).
3. En tu compu (o en la VM):
   ```bash
   export TELEGRAM_BOT_TOKEN="el-token-de-botfather"
   .venv/bin/python scripts/test_telegram.py     # te muestra tu CHAT_ID
   ```
4. Pegá ambos en `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
5. Verificá: `.venv/bin/python scripts/test_telegram.py` → te llega "Bot conectado".

---

## 2. Binance Testnet (paper trading — plata FALSA)

1. Entrá a **https://testnet.binance.vision** (login con GitHub).
2. Generá una **API Key** + **Secret** (HMAC).
3. Pegalas en `.env` y poné el modo en testnet:
   ```
   BOT_MODE=testnet
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
4. Verificá conexión y balance:
   ```bash
   set -a && . ./.env && set +a
   .venv/bin/python scripts/test_testnet.py
   ```
5. Primer aporte de prueba: `.venv/bin/python scripts/run_dca.py`

> La testnet te da saldo ficticio de USDT para practicar. Si BTC/USDT no tiene
> saldo, pedí fondos de prueba desde la misma web de testnet.

---

## 3. Oracle (correr 24/7 gratis)

Seguí **`docs/DEPLOY_ORACLE.md`** punta a punta. Resumen:
1. Crear VM ARM Always Free (Ubuntu, Tokyo).
2. Traer el código (git clone o scp).
3. `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`
4. Copiar tu `.env` a la VM.
5. Cron: `run_dca.py` diario + `dca_status.py` semanal (ya documentado).

---

## 4. ¿Dónde va cada cosa? (archivo `.env`)

Copiá `.env.example` a `.env` y completá:

| Variable | Para qué | Cuándo |
|---|---|---|
| `BOT_MODE` | `simulate` / `testnet` / `live` | siempre |
| `TELEGRAM_BOT_TOKEN` | alertas | paso 1 |
| `TELEGRAM_CHAT_ID` | alertas | paso 1 |
| `BINANCE_API_KEY` | órdenes | testnet (paso 2) / live (fase 3) |
| `BINANCE_API_SECRET` | órdenes | testnet (paso 2) / live (fase 3) |

`.env` está en `.gitignore` — **nunca se sube a git**.

---

## 5. ¿Necesito git? ¿O va todo en Oracle?

**Las dos cosas, son complementarias:**
- **GitHub** = dónde *vive* el código (fuente de verdad, respaldo, historial).
- **Oracle** = dónde el código *corre* 24/7.

El flujo natural: pusheás a GitHub (tu cuenta **personal**) → en Oracle hacés
`git clone` una vez, y `git pull` cada vez que cambiamos algo. Sin git también
funciona (copiás con `scp`), pero git hace las actualizaciones triviales.

**No es obligatorio**, pero es lo recomendado. Comandos para tu cuenta personal:
```bash
gh repo create thiagobrucezzi/crypto-trading-bot --private --source=. --push
# o manual:
git remote add origin https://github.com/thiagobrucezzi/crypto-trading-bot.git
git push -u origin <tu-rama>
```

---

## 6. Optimizar fees (opcional, ahorra centavos en DCA)

- **Pagar fees con BNB**: en Binance, activá "usar BNB para comisiones" → 0.1% baja a **0.075%**. Necesitás un saldo chico de BNB.
- **Par USDC**: operar `BTC/USDC` en vez de `BTC/USDT` → **0.095%** (o 0.071% con BNB).
- Si lo hacés, bajá `FEE_RATE` en `src/config.py` para que el reporte sea exacto.

> Para DCA con aportes chicos, las fees son centavos (ver `dca_backtest.py`).
> No te obsesiones — es nice-to-have, no cambia el resultado.

---

## 7. Comandos del día a día

```bash
.venv/bin/python scripts/run_dca.py        # aporta si toca (idempotente)
.venv/bin/python scripts/dca_status.py     # estado + análisis de salida
.venv/bin/python scripts/dca_ledger.py     # historial completo + CSV impuestos
.venv/bin/python scripts/dca_backtest.py   # validación histórica
.venv/bin/python tests/test_dca.py         # tests
```
