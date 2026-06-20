"""Estado del portafolio DCA, persistido en JSON (un archivo por modo).

Cada modo (simulate/testnet/live) tiene su propio estado para no mezclarlos.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Portfolio:
    def __init__(self, mode):
        self.mode = mode
        self.path = DATA_DIR / f"portfolio_{mode}.json"
        self.buys = []
        if self.path.exists():
            self.buys = json.loads(self.path.read_text()).get("buys", [])

    def save(self):
        DATA_DIR.mkdir(exist_ok=True)
        self.path.write_text(json.dumps({"buys": self.buys}, indent=2))

    def add_buy(self, fill, ts, period):
        rec = {"ts": ts, "period": period, **fill}
        self.buys.append(rec)
        self.save()
        return rec

    def bought_in_period(self, period):
        return any(b.get("period") == period for b in self.buys)

    def ledger(self):
        """Historial completo de compras, ordenado por fecha."""
        return sorted(self.buys, key=lambda b: b.get("ts", ""))

    def summary(self, prices):
        """prices: dict symbol -> precio actual. Devuelve P&L agregado y por activo."""
        agg = {}
        for b in self.buys:
            s = b["symbol"]
            d = agg.setdefault(s, {"units": 0.0, "invested": 0.0, "fees": 0.0, "n": 0})
            d["units"] += b["units"]
            d["invested"] += b["quote_spent"]
            d["fees"] += b.get("fee", 0.0)
            d["n"] += 1

        out = {"positions": {}, "invested": 0.0, "value": 0.0, "n_buys": len(self.buys)}
        for s, d in agg.items():
            price = prices.get(s, 0.0)
            value = d["units"] * price
            out["positions"][s] = {
                **d,
                "avg_cost": d["invested"] / d["units"] if d["units"] else 0.0,
                "price": price, "value": value, "pnl": value - d["invested"],
                "pnl_pct": (value / d["invested"] - 1) if d["invested"] else 0.0,
            }
            out["invested"] += d["invested"]
            out["value"] += value
        out["pnl"] = out["value"] - out["invested"]
        out["pnl_pct"] = (out["value"] / out["invested"] - 1) if out["invested"] else 0.0
        return out

    def exit_analysis(self, prices, fee_rate):
        """Qué pasaría si vendieras HOY (aritmética al precio actual, NO es consejo).

        Incluye: cuánto cobrarías neto, P&L realizado, qué fracción vender para
        recuperar lo invertido, y escenarios de venta parcial.
        """
        s = self.summary(prices)
        inv, val = s["invested"], s["value"]
        net_all = val * (1 - fee_rate)
        denom = val * (1 - fee_rate)
        frac_recover = (inv / denom) if denom > 0 else None
        scenarios = []
        for frac in (0.25, 0.50, 1.0):
            net = val * frac * (1 - fee_rate)
            cost = inv * frac  # costo proporcional de esa porción
            scenarios.append({
                "frac": frac, "net_proceeds": net, "pnl": net - cost,
                "remaining_value": val * (1 - frac),
            })
        return {
            "invested": inv, "value": val, "pnl_pct": s["pnl_pct"],
            "net_if_sell_all": net_all, "realized_all": net_all - inv,
            "frac_recover": frac_recover,
            "can_recover": frac_recover is not None and frac_recover <= 1.0,
            "scenarios": scenarios,
        }
