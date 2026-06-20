"""Lógica DCA: aporte periódico fijo a un activo (idempotente por período).

No re-compra si ya aportó en el período actual, así que es seguro correrlo
todos los días en el cron — solo ejecuta cuando toca (1x por mes/semana/día).
"""
from datetime import datetime, timezone

from src import config
from src.exchange import execute_buy, get_mode
from src.notifier import TelegramNotifier
from src.portfolio import Portfolio


def period_key(dt, freq):
    if freq == "daily":
        return dt.strftime("%Y-%m-%d")
    if freq == "weekly":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return dt.strftime("%Y-%m")  # monthly


def run_once(now=None, notify=True):
    now = now or datetime.now(timezone.utc)
    mode = get_mode()
    pf = Portfolio(mode)
    pk = period_key(now, config.DCA_FREQUENCY)

    if pf.bought_in_period(pk):
        print(f"DCA [{mode}]: ya se aportó en el período {pk}. Nada que hacer.")
        return None

    fill = execute_buy(config.DCA_SYMBOL, config.DCA_AMOUNT)
    rec = pf.add_buy(fill, now.isoformat(), pk)
    line = (f"🟢 <b>DCA ejecutado</b> [{mode}] — {pk}\n"
            f"{config.DCA_SYMBOL}: ${fill['quote_spent']:.2f} → "
            f"{fill['units']:.6f} @ ${fill['price']:,.2f}")
    if notify:
        TelegramNotifier().send(line)
    print(line.replace("<b>", "").replace("</b>", ""))
    return rec
