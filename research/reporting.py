"""Genera un reporte HTML autocontenido con graficos (PNG embebidos en base64).

Muestra honestamente el comportamiento de la estrategia vs benchmarks, con una
linea vertical en la particion TRAIN/TEST para que se vea si hubo overfitting.
"""
import base64
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from research.backtest_momentum import (  # noqa: E402
    backtest, buy_and_hold, equal_weight, metrics,
)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _metric_card(label, value, good=None):
    color = "#1f2937"
    if good is True:
        color = "#15803d"
    elif good is False:
        color = "#b91c1c"
    return (f'<div class="card"><div class="card-label">{label}</div>'
            f'<div class="card-value" style="color:{color}">{value}</div></div>')


def _row(name, m, highlight=False):
    cls = ' class="hl"' if highlight else ""
    return (f"<tr{cls}><td>{name}</td>"
            f"<td>{m['total_return']*100:,.0f}%</td>"
            f"<td>{m['cagr']*100:,.1f}%</td>"
            f"<td style='color:#b91c1c'>{m['max_drawdown']*100:,.1f}%</td>"
            f"<td>{m['volatility']*100:,.0f}%</td>"
            f"<td>{m['sharpe']:.2f}</td>"
            f"<td>{m['calmar']:.2f}</td></tr>")


def generate(prices, params, split, out_path=None):
    out_path = Path(out_path) if out_path else REPORTS_DIR / "report.html"
    out_path.parent.mkdir(exist_ok=True)
    split_ts = __import__("pandas").Timestamp(split, tz="UTC")

    res = backtest(prices, fee_rate=params["fee_rate"], slippage=params["slippage"],
                   regime_symbol=params["regime_symbol"], regime_sma=params["regime_sma"],
                   top_n=params["top_n"], lookbacks=params["lookbacks"],
                   rebalance_days=params["rebalance_days"], stop_loss=params["stop_loss"],
                   asset_trend_sma=params.get("asset_trend_sma"))
    eq = res["equity"]
    dates = eq.index
    bh_btc = buy_and_hold(prices, "BTC/USDT", dates)
    bh_eth = buy_and_hold(prices, "ETH/USDT", dates)
    ew = equal_weight(prices, dates)

    # --- Chart 1: equity (log) ---
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(dates, eq, label="Estrategia (momentum)", color="#2563eb", lw=2.2)
    ax.plot(dates, bh_btc, label="Buy&Hold BTC", color="#f59e0b", lw=1.2, alpha=.8)
    ax.plot(dates, bh_eth, label="Buy&Hold ETH", color="#6b7280", lw=1.2, alpha=.7)
    ax.plot(dates, ew, label="Equal-Weight", color="#10b981", lw=1.2, alpha=.7)
    ax.axvline(split_ts, color="#dc2626", ls="--", lw=1.5)
    ax.text(split_ts, ax.get_ylim()[1], "  TRAIN | TEST (a ciegas)", color="#dc2626",
            va="top", fontsize=9, fontweight="bold")
    ax.set_yscale("log")
    ax.set_title("Curva de capital (escala log) — $1 inicial", fontsize=13, fontweight="bold")
    ax.set_ylabel("Capital (x)")
    ax.legend(loc="upper left", fontsize=9)
    chart_equity = _fig_to_b64(fig)

    # --- Chart 2: drawdown underwater ---
    dd = eq / eq.cummax() - 1
    fig, ax = plt.subplots(figsize=(11, 3))
    ax.fill_between(dates, dd * 100, 0, color="#dc2626", alpha=.35)
    ax.plot(dates, dd * 100, color="#dc2626", lw=1)
    ax.axvline(split_ts, color="#111827", ls="--", lw=1.2)
    ax.set_title("Drawdown (cuanto perdes desde el ultimo pico)", fontsize=13, fontweight="bold")
    ax.set_ylabel("%")
    chart_dd = _fig_to_b64(fig)

    # --- Chart 3: exposure ---
    fig, ax = plt.subplots(figsize=(11, 2.5))
    ax.fill_between(dates, res["exposure"] * 100, 0, color="#2563eb", alpha=.3, step="pre")
    ax.axvline(split_ts, color="#111827", ls="--", lw=1.2)
    ax.set_title("Exposicion al mercado (% invertido vs cash por filtro de regimen)",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("%")
    ax.set_ylim(0, 105)
    chart_exp = _fig_to_b64(fig)

    # --- metrics: full / train / test ---
    m_full = metrics(eq)
    m_train = metrics(eq[dates < split_ts])
    m_test = metrics(eq[dates >= split_ts])

    overfit_gap = m_train["calmar"] - m_test["calmar"]
    verdict_ok = m_test["sharpe"] >= 1.0 and m_test["max_drawdown"] > -0.40

    html = f"""<title>Reporte Backtest — Momentum Bot</title>
<style>
  :root {{ font-family: -apple-system, system-ui, sans-serif; color: #1f2937; }}
  body {{ max-width: 1000px; margin: 0 auto; padding: 24px; line-height: 1.5; }}
  h1 {{ font-size: 26px; margin-bottom: 4px; }}
  .sub {{ color: #6b7280; margin-bottom: 24px; }}
  .banner {{ padding: 16px 20px; border-radius: 12px; margin: 20px 0;
            background: {'#dcfce7' if verdict_ok else '#fef2f2'};
            border: 1px solid {'#86efac' if verdict_ok else '#fecaca'}; }}
  .banner h2 {{ margin: 0 0 6px; font-size: 17px;
               color: {'#15803d' if verdict_ok else '#b91c1c'}; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; }}
  .card {{ flex: 1; min-width: 130px; background: #f9fafb; border: 1px solid #e5e7eb;
          border-radius: 10px; padding: 12px 14px; }}
  .card-label {{ font-size: 11px; text-transform: uppercase; color: #6b7280; letter-spacing: .04em; }}
  .card-value {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
  img {{ max-width: 100%; border-radius: 10px; border: 1px solid #e5e7eb; margin: 8px 0 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0 24px; font-size: 14px; }}
  th, td {{ text-align: right; padding: 8px 10px; border-bottom: 1px solid #eee; }}
  th:first-child, td:first-child {{ text-align: left; }}
  thead th {{ background: #f3f4f6; font-size: 12px; text-transform: uppercase; color: #374151; }}
  tr.hl {{ background: #eff6ff; font-weight: 600; }}
  .foot {{ color: #9ca3af; font-size: 12px; margin-top: 32px; }}
  code {{ background: #f3f4f6; padding: 1px 6px; border-radius: 4px; }}
</style>

<h1>🤖 Reporte de Backtest — Estrategia Momentum</h1>
<div class="sub">Rotacion por fuerza relativa + filtro de regimen + stop-loss.
Periodo {dates[0].date()} → {dates[-1].date()}. Costos: fee {params['fee_rate']*100:.2f}% + slippage {params['slippage']*100:.2f}%.</div>

<div class="banner">
  <h2>{'✅ La estrategia se sostiene fuera de muestra' if verdict_ok else '⚠️ Señal de overfitting — NO apta para capital real todavia'}</h2>
  En datos de entrenamiento el Calmar fue <b>{m_train['calmar']:.2f}</b>; en datos nuevos a ciegas (TEST)
  cayo a <b>{m_test['calmar']:.2f}</b>. Una caida grande = la estrategia estaba ajustada al pasado.
  El numero honesto que esperamos hacia adelante es el de <b>TEST</b>, no el de TRAIN.
</div>

<div class="cards">
  {_metric_card("CAGR (TEST)", f"{m_test['cagr']*100:.1f}%")}
  {_metric_card("Max Drawdown (TEST)", f"{m_test['max_drawdown']*100:.0f}%", good=m_test['max_drawdown']>-0.40)}
  {_metric_card("Sharpe (TEST)", f"{m_test['sharpe']:.2f}", good=m_test['sharpe']>=1.0)}
  {_metric_card("Calmar (TEST)", f"{m_test['calmar']:.2f}", good=m_test['calmar']>=1.0)}
  {_metric_card("Stop-loss disparados", str(res['n_stops']))}
</div>

<img src="data:image/png;base64,{chart_equity}" alt="equity">
<img src="data:image/png;base64,{chart_dd}" alt="drawdown">
<img src="data:image/png;base64,{chart_exp}" alt="exposure">

<h3>Métricas por período</h3>
<table>
  <thead><tr><th>Período</th><th>Total</th><th>CAGR</th><th>Max DD</th><th>Vol</th><th>Sharpe</th><th>Calmar</th></tr></thead>
  <tbody>
    {_row("TRAIN (lo que el modelo vio)", m_train)}
    {_row("TEST (a ciegas)", m_test, highlight=True)}
    {_row("Período completo", m_full)}
  </tbody>
</table>

<h3>Estrategia vs comprar y aguantar (período completo)</h3>
<table>
  <thead><tr><th>Estrategia</th><th>Total</th><th>CAGR</th><th>Max DD</th><th>Vol</th><th>Sharpe</th><th>Calmar</th></tr></thead>
  <tbody>
    {_row("Momentum (esta estrategia)", m_full, highlight=True)}
    {_row("Buy&Hold BTC", metrics(bh_btc))}
    {_row("Buy&Hold ETH", metrics(bh_eth))}
    {_row("Equal-Weight (todas)", metrics(ew))}
  </tbody>
</table>

<div class="foot">
  Config: top_n={params['top_n']}, lookbacks={params['lookbacks']}, rebalance={params['rebalance_days']}d,
  stop_loss={params['stop_loss']}, asset_trend_sma={params.get('asset_trend_sma')}.<br>
  Lectura: <code>CAGR</code> retorno anual compuesto · <code>Max DD</code> peor caída desde un pico ·
  <code>Sharpe</code> &gt;1 bien, &gt;2 muy bien · <code>Calmar</code> CAGR/|MaxDD| (ganancia por unidad de dolor).<br>
  ⚠️ Resultados de backtest. Sesgo de supervivencia en el universo elegido. No es asesoramiento financiero.
</div>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path, {"train": m_train, "test": m_test, "full": m_full, "verdict_ok": verdict_ok}
