"""Lógica DCA: aporte periódico fijo a un activo (idempotente por período).

No re-compra si ya aportó en el período actual, así que es seguro correrlo
todos los días en el cron — solo ejecuta cuando toca (1x por mes/semana/día).

Resiliencia: si el aporte falla (red, exchange caído, sin saldo), avisa por
Telegram en vez de fallar en silencio, y propaga el error (exit != 0 en el cron).
"""
from datetime import date, datetime, timedelta, timezone

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


def next_period_date(now, freq):
    """Fecha aproximada del próximo aporte (para mostrar en el reporte)."""
    if freq == "daily":
        return (now + timedelta(days=1)).date()
    if freq == "weekly":
        return (now + timedelta(days=7)).date()
    y, m = now.year, now.month
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def run_once(now=None, notify=True):
    now = now or datetime.now(timezone.utc)
    mode = get_mode()
    notifier = TelegramNotifier()
    pf = Portfolio(mode)
    pk = period_key(now, config.DCA_FREQUENCY)

    if pf.bought_in_period(pk):
        print(f"DCA [{mode}]: ya se aportó en el período {pk}. Nada que hacer.")
        return None

    try:
        fill = execute_buy(config.DCA_SYMBOL, config.DCA_AMOUNT)
        rec = pf.add_buy(fill, now.isoformat(), pk)
    except Exception as e:  # noqa: BLE001
        alert = (f"⚠️ <b>DCA FALLÓ</b> [{mode}] — {pk}\n"
                 f"{config.DCA_SYMBOL}: el aporte NO se ejecutó.\n"
                 f"Motivo: {type(e).__name__}: {e}\n"
                 f"Revisá el bot (no se gastó nada).")
        print(alert.replace("<b>", "").replace("</b>", ""))
        if notify:
            notifier.send(alert)
        raise

    line = (f"🟢 <b>DCA ejecutado</b> [{mode}] — {pk}\n"
            f"{config.DCA_SYMBOL}: ${fill['quote_spent']:.2f} → "
            f"{fill['units']:.6f} @ ${fill['price']:,.2f}")
    if notify:
        notifier.send(line)
    print(line.replace("<b>", "").replace("</b>", ""))
    return rec
