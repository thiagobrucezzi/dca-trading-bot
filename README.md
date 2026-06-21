# dca-trading-bot

A simple, honest **Dollar-Cost Averaging (DCA)** bot for Binance — with Telegram
alerts and free 24/7 hosting on Oracle Cloud. Philosophy: **don't lose money first**.

Fork it, point it at your own Binance + Telegram, and run your own DCA. It's designed
to be safe to learn with: you start with a no-money simulation, move to the testnet
(fake money), and only go live with real money when *you* decide.

> ⚠️ **Not financial advice.** Educational/personal tool, provided as-is. You are
> responsible for your own funds and decisions.

---

## What it is

DCA means buying a **fixed amount** of an asset on a **fixed schedule**, regardless
of price. You stop trying to time the market and instead average your entry over
time. It's boring on purpose — and that's the point.

This bot automates that: it runs on a tiny server, buys BTC on your schedule, sends
you a Telegram message for every buy, and reports your portfolio with a P&L and an
"if you sold today" analysis. **It only ever buys — selling is your decision.**

### Why DCA, and not a "smart" predictive bot?

This project started as a predictive bot. We built two strategies and validated them
honestly (walk-forward + an untouched holdout):

- **Momentum rotation** → overfitting. Out-of-sample Sharpe ~0.5-0.8, drawdown -50/-60%. ❌
- **Mean-reversion** → multi-fold walk-forward 0/4 passed, avg OOS Sharpe -0.26. ❌

Neither cleared the bar (Sharpe ≥ 1.0, MaxDD > -35%). The honest lesson: simple
technical strategies on liquid daily crypto have no durable edge after costs. So a
plain DCA becomes the strategy **and** the benchmark any future bot must beat in
out-of-sample testing to earn real money. The research is archived in `research/`.

### Key properties

- **Buy-only** by design.
- **Idempotent** — the scheduler runs daily, but only buys once per period.
- **Resilient** — if a buy fails, it alerts you on Telegram instead of dying silently.
- **3 modes** (`BOT_MODE`): `simulate` (no keys) → `testnet` (fake money) → `live` (real).

---

## Step 1 — Install and test locally (no money, no keys)

```bash
git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
cd dca-trading-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # default BOT_MODE=simulate
```

Run it right now — **simulate** mode needs no API keys and spends nothing. It just
records a buy at the current public price so you can see the whole flow:

```bash
.venv/bin/python scripts/run_dca.py        # records a simulated buy
.venv/bin/python scripts/dca_status.py     # portfolio status + exit analysis
.venv/bin/python tests/test_dca.py         # run the tests (no network, no keys)
```

If that works, the bot is healthy. Now let's connect the real pieces.

---

## Step 2 — Connect Telegram (alerts)

1. In Telegram, message **@BotFather** → `/newbot` → copy the **token**.
2. Send any message to your new bot (so the chat exists).
3. Get your chat id:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token"
   .venv/bin/python scripts/test_telegram.py     # prints your CHAT_ID
   ```
4. Put both in `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
5. Verify: `.venv/bin/python scripts/test_telegram.py` → you receive "Bot connected".

---

## Step 3 — Connect Binance Testnet (fake money) & load the API keys

The testnet is a full copy of Binance with **fake funds** — perfect for testing
without risk. It even funds you automatically.

**Get your testnet API keys:**
1. Go to **https://testnet.binance.vision** → **log in with GitHub**.
2. Click **"Generate HMAC_SHA256 Key"**.
3. **Description**: a short name (e.g. `dca-bot`).
4. **Permissions**: enable **TRADE** + **USER_DATA**. *Without TRADE the bot can't buy.*
5. **Commission**: choose **0.1%** (realistic), not "none".
6. **Save the API Key + Secret immediately** — the Secret is shown **only once**.

**Load them and test (this is where you "fund" — testnet does it for you):**
```bash
# in .env:
#   BOT_MODE=testnet
#   BINANCE_API_KEY=...
#   BINANCE_API_SECRET=...
set -a && . ./.env && set +a
.venv/bin/python scripts/test_testnet.py    # ✅ connection + balance (~10,000 fake USDT)
.venv/bin/python scripts/run_dca.py          # first real testnet buy (fake money)
.venv/bin/python scripts/dca_status.py       # status to Telegram
```

> Testnet auto-funds you and **resets ~monthly** (wipes balances/orders, keeps your
> keys). It's a sandbox — great for validating that everything works for days/weeks.

---

## Step 4 — Choose your DCA settings (and how often to buy)

Set these in `.env` (no code changes needed):

```
DCA_SYMBOL=BTC/USDT
DCA_AMOUNT=50            # quote (USDT) per buy
DCA_FREQUENCY=monthly    # monthly | weekly | daily
```

### How often should you buy? (the fee myth)

A common worry: "won't more frequent buys cost me more in fees?" **No** — Binance
fees are a **percentage** of each trade (0.1%), not a flat fee. 0.1% of $50 is $0.05
whether you do 1 buy or 4. So splitting your monthly amount across more buys costs
the **same total fee**, and it **smooths your average entry price** (you depend less
on a single day's luck).

The real limit is the **minimum order size** (~$5-10 on BTC/USDT):

| Frequency | For $50/month | Total fee/month | Notes |
|---|---|---|---|
| `monthly` | 1 × $50 | ~$0.05 | simplest |
| `weekly` | 4 × $12.50 | ~$0.05 (same) | smoother, clears the minimum ✅ |
| `daily` | ~30 × $1.67 | ~$0.05 (same) | ❌ below the minimum → rejected |

**Rule of thumb:** `weekly` is a great default — smoother than monthly at no extra
fee cost. Only use `daily` if each buy is ≥ ~$10 (i.e. larger monthly budgets).
Don't try to "buy the dip" / time the price — that's exactly what DCA replaces.

---

## Step 5 — Deploy 24/7 on Oracle Cloud (free)

So it runs without your laptop on. Full guide: [`docs/DEPLOY_ORACLE.md`](docs/DEPLOY_ORACLE.md).

1. **Network**: Networking → VCN → *Start VCN Wizard* → "VCN with Internet
   Connectivity" (creates VCN + public subnet + internet gateway).
2. **VM**: Compute → Instances → Create → Ubuntu 24.04 · Shape **VM.Standard.A1.Flex**
   (or **E2.1.Micro** if A1 is "out of capacity") · **Always Free**. In Networking,
   pick the public subnet and enable **"Automatically assign public IPv4 address"**.
   Generate and **download the SSH private key**.
3. **Deploy**:
   ```bash
   chmod 600 ~/Downloads/ssh-key-*.key
   ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
   # on the VM:
   sudo apt update && sudo apt install -y python3.12-venv git
   git clone https://github.com/thiagobrucezzi/dca-trading-bot.git
   cd dca-trading-bot && python3 -m venv .venv && .venv/bin/pip install ccxt
   nano .env          # paste your testnet .env
   set -a && . ./.env && set +a && .venv/bin/python scripts/test_testnet.py
   ```
4. **Schedule it** — `crontab -e`:
   ```cron
   5  9 * * *  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/run_dca.py    >> bot.log 2>&1
   10 9 * * 1  cd ~/dca-trading-bot && set -a && . ./.env && set +a && .venv/bin/python scripts/dca_status.py >> bot.log 2>&1
   ```
   `run_dca.py` runs daily but only buys once per period. Times are **UTC**.

---

## Step 6 — Go LIVE with real money (only when ready)

After weeks of clean testnet runs:

1. **Fund your real Binance account**: deposit/buy **USDT** in your Spot wallet
   (the bot spends USDT to buy BTC). Keep enough USDT for your planned buys.
2. **Create real API keys** on Binance → **Spot Trading only**. **NEVER enable
   withdrawals.** Whitelist your VM's public IP.
3. In `.env`: `BOT_MODE=live` + the real keys. Set `DCA_FREQUENCY` (e.g. `weekly`)
   and a `DCA_AMOUNT` you're comfortable with.

The same code you already tested now buys **real** BTC on your schedule, with the
same alerts, reports and resilience. **It never sells — that's your call.**

---

## Configuration reference (`.env`)

| Variable | Purpose | Default |
|---|---|---|
| `BOT_MODE` | `simulate` / `testnet` / `live` | `simulate` |
| `TELEGRAM_BOT_TOKEN` / `_CHAT_ID` | alerts | — |
| `BINANCE_API_KEY` / `_SECRET` | orders (testnet/live) | — |
| `DCA_SYMBOL` | asset | `BTC/USDT` |
| `DCA_AMOUNT` | quote (USDT) per buy | `50` |
| `DCA_FREQUENCY` | `monthly` / `weekly` / `daily` | `monthly` |

`.env` is in `.gitignore` — **never commit it**.

## Everyday commands

```bash
.venv/bin/python scripts/run_dca.py        # buy if a period is due (idempotent)
.venv/bin/python scripts/dca_status.py     # status + P&L + exit analysis
.venv/bin/python scripts/dca_ledger.py     # full history + transactions CSV
.venv/bin/python scripts/dca_backtest.py   # historical DCA validation (fees + IRR)
```

## Project structure

```
src/          config, exchange (simulate/testnet/live), portfolio, dca, notifier
scripts/      run_dca, dca_status, dca_ledger, dca_backtest, dca_demo, test_telegram, test_testnet
tests/        test_dca.py
research/      failed strategies + walk-forward harness (archived, standby)
docs/          SETUP.md, DEPLOY_ORACLE.md
```

## Contributing

PRs welcome — especially research strategies that beat plain DCA in walk-forward.
Keep secrets out of commits. Educational software, no warranty. **Not financial advice.**
