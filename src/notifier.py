"""Notificador de Telegram (stdlib, sin dependencias extra).

Configuracion por variables de entorno (ver .env.example):
  TELEGRAM_BOT_TOKEN  -> el token que te da @BotFather
  TELEGRAM_CHAT_ID    -> tu chat id (se obtiene con scripts/test_telegram.py)

Si no esta configurado, hace no-op y loguea por consola (no rompe el bot).
"""
import json
import os
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)

    def _call(self, method, params):
        url = API.format(token=self.token, method=method)
        data = urllib.parse.urlencode(params).encode()
        with urllib.request.urlopen(url, data=data, timeout=15) as r:
            return json.loads(r.read().decode())

    def send(self, text, silent=False):
        if not self.enabled:
            print(f"[notifier:OFF] {text}")
            return None
        try:
            return self._call("sendMessage", {
                "chat_id": self.chat_id, "text": text,
                "parse_mode": "HTML", "disable_notification": silent,
            })
        except Exception as e:  # noqa: BLE001
            print(f"[notifier:ERROR] {e}\n{text}")
            return None


def fmt_trade(action, symbol, qty, price, reason=""):
    icon = "🟢" if action.upper() == "BUY" else "🔴"
    extra = f"\n<i>{reason}</i>" if reason else ""
    return (f"{icon} <b>{action.upper()} {symbol}</b>\n"
            f"Cantidad: {qty:.6f}\nPrecio: ${price:,.2f}{extra}")


def fmt_daily(signal, equity=None, pnl_pct=None):
    d = signal["date"].date() if hasattr(signal["date"], "date") else signal["date"]
    regime = "🟢 ALCISTA (operando)" if signal["regime_on"] else "🔴 BAJISTA (en cash)"
    lines = [f"📊 <b>Reporte diario — {d}</b>",
             f"Régimen BTC: {regime}  ({signal['btc_vs_sma200']*100:+.1f}% vs SMA200)"]
    if signal["in_cash"]:
        lines.append("Posición: <b>100% CASH</b> (sin señales válidas)")
    else:
        w = ", ".join(f"{a.split('/')[0]} {v*100:.0f}%" for a, v in signal["target_weights"].items())
        lines.append(f"Portafolio objetivo: <b>{w}</b>")
    lines.append("\n<b>Top ranking momentum:</b>")
    for a, sc in signal["ranking"][:5]:
        lines.append(f"  {a.split('/')[0]:5s} {sc*100:+6.1f}%")
    if equity is not None:
        lines.append(f"\n💰 Capital: ${equity:,.2f}")
    if pnl_pct is not None:
        lines.append(f"📈 P&L acumulado: {pnl_pct*100:+.1f}%")
    return "\n".join(lines)
