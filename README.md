# dca-trading-bot

A simple, honest **Dollar-Cost Averaging (DCA)** bot for Binance — with Telegram
alerts and free 24/7 deployment on Oracle Cloud. Philosophy: **don't lose money first**.

Fork it, point it at your own Binance + Telegram, and run your own DCA. It's built
to be safe to learn with: start in a no-money simulation, graduate to the testnet
(fake money), and only go live when *you* decide.

> ⚠️ **Not financial advice.** This is an educational/personal tool. You are
> responsible for your own funds and decisions.

---

## 📖 Why DCA (and not a "smart" bot)

This project started as an attempt to build a predictive trading bot. We tried two
strategies with rigorous validation (walk-forward + an untouched holdout):

- **Momentum rotation** → overfitting. Out-of-sample Sharpe ~0.5-0.8, drawdown -50/-60%. ❌
- **Mean-reversion** → multi-fold walk-forward 0/4 folds passed, avg OOS Sharpe -0.26. ❌

**Neither cleared the bar** (Sharpe ≥ 1.0 and MaxDD > -35%). The honest conclusion:
simple technical strategies on liquid daily crypto have no durable edge after costs.
So a **plain DCA on BTC** becomes both the strategy and the **benchmark any future
bot must beat in out-of-sample validation** to deserve real money. The failed
research lives in `research/` (kept as the walk-forward harness).

---

## ⚙️ How it works

- **DCA**: buys a fixed amount of BTC every fixed period, regardless of price. It
  doesn't predict anything; it rides the long-term trend and averages your entry.
- **Buy-only by design.** Selling is your decision, never the bot's.
- **Idempotent**: the cron runs daily, but it only buys once per period
  (month/week/day). Running it again does nothing.
- **Resilient**: if a buy fails (network, exchange down, no balance), it alerts you
  on Telegram instead of failing silently.
- **3 modes** (`BOT_MODE`):
  - `simulate` — no API keys, records at the public price. Start here.
  - `testnet` — real orders on Binance testnet (**fake** money).
  - `live` — **real** money (only when you choose).

---

## 🚀 Setup

### 0. Local

```bash
git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
cd dca-trading-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Run it immediately in simulation (no keys needed):
```bash
.venv/bin/python scripts/run_dca.py        # records a buy at the live public price
.venv/bin/python scripts/dca_status.py     # portfolio status + exit analysis
```

### 1. Telegram (alerts & reports)

1. In Telegram, talk to **@BotFather** → `/newbot` → copy the **token**.
2. Send any message to your new bot (so the chat exists).
3. Get your chat id:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   .venv/bin/python scripts/test_telegram.py     # prints your CHAT_ID
   ```
4. Fill in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```

### 2. Binance Testnet (paper trading, fake money)

How to get testnet API keys, step by step:

1. Go to **https://testnet.binance.vision** and **log in with GitHub**.
2. Click **"Generate HMAC_SHA256 Key"**.
3. **Description**: a short name (e.g. `dca-bot`).
4. **Key permissions**: enable **TRADE** (place orders) and **USER_DATA** (read
   balance). `USER_STREAM` is optional. *Without TRADE the bot cannot buy.*
5. **Commission**: pick **0.1%** (not "none") to simulate realistic conditions.
6. **Save the API Key and Secret now** — the Secret is shown **only once**.
7. Fill in `.env`:
   ```
   BOT_MODE=testnet
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
8. Validate and make the first buy:
   ```bash
   set -a && . ./.env && set +a
   .venv/bin/python scripts/test_testnet.py    # ✅ connection + balance (gives ~10,000 fake USDT)
   .venv/bin/python scripts/run_dca.py          # first buy (testnet)
   .venv/bin/python scripts/dca_status.py       # status to Telegram
   ```

> **Testnet notes:** it auto-funds you with fake balances and **resets ~monthly**
> (wipes balances/orders) while **keeping your API keys**. Only `/api` (spot)
> endpoints work; no withdrawals.

### 3. Deploy on Oracle Cloud (free 24/7)

Full guide: [`docs/DEPLOY_ORACLE.md`](docs/DEPLOY_ORACLE.md). Summary:

1. **Create the network**: Networking → VCN → *Start VCN Wizard* → "VCN with
   Internet Connectivity" (creates VCN + public subnet + internet gateway).
2. **Create the VM**: Compute → Instances → Create:
   - Ubuntu 24.04 · Shape **VM.Standard.A1.Flex** (or **E2.1.Micro** if A1 is "out
     of capacity") · **Always Free**
   - Networking → pick the VCN and the **public subnet** → enable
     **"Automatically assign public IPv4 address"**
   - SSH keys → generate and **download the private key**
3. **Connect and deploy**:
   ```bash
   chmod 600 ~/Downloads/ssh-key-*.key
   ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
   # on the VM:
   sudo apt update && sudo apt install -y python3.12-venv git
   git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
   cd dca-trading-bot && python3 -m venv .venv && .venv/bin/pip install ccxt
   nano .env          # paste your .env (testnet)
   set -a && . ./.env && set +a
   .venv/bin/python scripts/test_testnet.py
   ```

### 4. Cron (run automatically)

On the VM, `crontab -e`:
```cron
5  9 * * *  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/run_dca.py    >> bot.log 2>&1
10 9 * * 1  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/dca_status.py >> bot.log 2>&1
```
`run_dca.py` runs daily but only buys once per `DCA_FREQUENCY` period. Times are
**UTC**.

### 5. Going LIVE (real money — only when you're ready)

After weeks of testnet running cleanly:
1. Create API keys on your **real** Binance account → **Spot Trading only**.
   **NEVER enable withdrawals.** Whitelist the VM's public IP.
2. In `.env`: `BOT_MODE=live` + the real keys.
3. Start with a small `DCA_AMOUNT`.

---

## 🔧 Configuration (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `BOT_MODE` | `simulate` / `testnet` / `live` | `simulate` |
| `TELEGRAM_BOT_TOKEN` | alerts | — |
| `TELEGRAM_CHAT_ID` | alerts | — |
| `BINANCE_API_KEY` / `_SECRET` | orders (testnet/live) | — |
| `DCA_SYMBOL` | asset | `BTC/USDT` |
| `DCA_AMOUNT` | quote (USDT) per buy | `50` |
| `DCA_FREQUENCY` | `monthly` / `weekly` / `daily` | `monthly` |

Fees in `src/config.py` (`FEE_RATE`): 0.1% standard, 0.075% with BNB, 0.095% USDC
pairs. `.env` is in `.gitignore` — **never committed**.

---

## 🖥️ Everyday commands

```bash
.venv/bin/python scripts/run_dca.py        # buy if a period is due (idempotent)
.venv/bin/python scripts/dca_status.py     # status + P&L + exit analysis
.venv/bin/python scripts/dca_ledger.py     # full history + transactions CSV
.venv/bin/python scripts/dca_backtest.py   # historical DCA validation (fees + IRR)
.venv/bin/python tests/test_dca.py         # tests (no network, no keys)
```

---

## 📂 Structure

```
src/          config, exchange (simulate/testnet/live), portfolio, dca, notifier
scripts/      run_dca, dca_status, dca_ledger, dca_backtest, dca_demo, test_telegram, test_testnet
tests/        test_dca.py
research/      failed strategies + walk-forward harness (archived, standby)
docs/         SETUP.md, DEPLOY_ORACLE.md
```

---

## 🔬 Research (standby)

A predictive strategy only graduates to `live` if it **beats the DCA in honest
out-of-sample validation**. The 2025-06 → 2026-06 holdout is kept **untouched** for
that test. See `research/README.md`.

---

## Contributing

PRs welcome — especially research strategies that beat plain DCA in walk-forward.
Keep secrets out of commits (`.env` is gitignored). This is educational software,
provided as-is, with no warranty. **Not financial advice.**
