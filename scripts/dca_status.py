"""Reporte del estado del portafolio DCA (consola + Telegram).

Incluye: aportes, costo promedio, P&L actual, y un ANÁLISIS DE SALIDA
(cuánto cobrarías si vendieras hoy, qué porción para recuperar capital,
escenarios de venta parcial). Es aritmética al precio actual, NO es consejo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.exchange import get_mode, get_price
from src.notifier import TelegramNotifier
from src.portfolio import Portfolio


def build_message():
    mode = get_mode()
    pf = Portfolio(mode)
    if not pf.buys:
        return f"📊 DCA [{mode}]: todavía no hay aportes registrados."

    symbols = {b["symbol"] for b in pf.buys}
    prices = {s: get_price(s) for s in symbols}
    s = pf.summary(prices)
    ex = pf.exit_analysis(prices, config.FEE_RATE)

    arrow = "📈" if s["pnl"] >= 0 else "📉"
    L = [f"📊 <b>Estado DCA</b> [{mode}] — {s['n_buys']} aportes",
         f"Invertido: ${s['invested']:,.2f}",
         f"Valor actual: ${s['value']:,.2f}",
         f"{arrow} P&L no realizado: ${s['pnl']:+,.2f} ({s['pnl_pct']*100:+.1f}%)",
         ""]
    for sym, p in s["positions"].items():
        L.append(f"<b>{sym}</b>: {p['units']:.6f} u")
        L.append(f"  costo prom ${p['avg_cost']:,.2f} | precio ${p['price']:,.2f}")

    L.append("\n🎯 <b>Análisis de salida</b> (al precio actual, no es recomendación)")
    if ex["realized_all"] >= 0:
        L.append(f"  Si vendés TODO: cobrás ${ex['net_if_sell_all']:,.2f} "
                 f"→ ganancia ${ex['realized_all']:+,.2f}")
    else:
        L.append(f"  Si vendés TODO: cobrás ${ex['net_if_sell_all']:,.2f} "
                 f"→ pérdida ${ex['realized_all']:+,.2f}")
    if ex["can_recover"]:
        L.append(f"  Para recuperar lo invertido: vender {ex['frac_recover']*100:.0f}% de tu BTC")
    else:
        L.append("  A este precio NO alcanza para recuperar lo invertido (estás abajo del costo)")
    L.append("  Escenarios de venta parcial:")
    for sc in ex["scenarios"]:
        L.append(f"   {sc['frac']*100:>3.0f}% → cobrás ${sc['net_proceeds']:,.2f} "
                 f"(P&L ${sc['pnl']:+,.2f}) | te quedan ${sc['remaining_value']:,.2f} en BTC")
    return "\n".join(L)


if __name__ == "__main__":
    msg = build_message()
    TelegramNotifier().send(msg)
    print(msg.replace("<b>", "").replace("</b>", ""))
