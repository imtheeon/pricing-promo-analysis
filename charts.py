"""Plotly chart helpers for app.py. One accent for the key finding, greys for everything else."""
import math
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
import plotly.graph_objects as go

ACC, BLUE, GREY, TXT, GRID = "#D55E00", "#0072B2", "#9E9E9E", "#4D4D4D", "#D9D9D9"
BANDS = ["0%", "1-20%", "21-40%", ">40%"]
MODEL = {"snaive": "Seasonal naive", "ets_add_notrend": "ETS (A,N,A)"}
SERIES = {"sales": "Net sales", "profit": "Profit"}


def half_up(v, nd=0):
    """Round half away from zero (3304.5 -> 3305): the one rounding rule for every displayed figure."""
    return float(Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-nd), ROUND_HALF_UP))


def usd(v):
    v = half_up(v)
    return f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"


def usdk(v, nd=1):
    """$K label as in the static PNGs: -$20K, $0, $2.5K."""
    k = half_up(v / 1e3, nd)
    return "$0" if k == 0 else f"{'-' if k < 0 else ''}${abs(k):,.{nd}f}".removesuffix(".0") + "K"


def usd_ticks(lo, hi):
    """Plotly tickvals/ticktext for a dollar axis spanning lo..hi (and 0), about 5 steps of 1/2/2.5/5 x 10^n."""
    lo, hi = min(lo, 0), max(hi, 0)
    span = max(hi - lo, 1)
    step = 10 ** math.floor(math.log10(span / 5))
    step *= next(m for m in (1, 2, 2.5, 5, 10) if span / (step * m) <= 6)
    ticks = [i * step for i in range(math.floor(lo / step), math.ceil(hi / step) + 1)]
    return dict(tickvals=ticks, ticktext=[usdk(t) for t in ticks])


def finish(fig, title, x, y, h=360, **kw):
    fig.update_layout(title=dict(text=title, font_size=15, x=0), xaxis_title=x, yaxis_title=y, height=h,
                      font=dict(family="Inter, Arial, sans-serif", color=TXT), paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(t=60, b=70, l=10, r=10), legend=dict(orientation="h", y=-0.28, title_text=""), **kw)
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def note(fig, x, y, text, ax=0, ay=-40):
    fig.add_annotation(x=x, y=y, text=text, showarrow=True, arrowcolor=ACC, ax=ax, ay=ay, font=dict(color=ACC, size=12))


def bars(r, x, y, key, title, xt, yt, fmt, hover, tickformat=None):
    """Sorted-by-input bars; `key` is the one highlighted category, rest grey."""
    fig = go.Figure(go.Bar(x=r[x], y=r[y], text=r[y].map(fmt), textposition="outside", cliponaxis=False,
                           marker_color=[ACC if k == key else GREY for k in r[x]], hovertemplate=hover + "<extra></extra>"))
    fig.update_yaxes(tickformat=tickformat)
    return finish(fig, title, xt, yt)


def subcat(g, title):
    worst = g.loc[g["profit"].idxmin()]
    fig = go.Figure(go.Scatter(x=g["discount_usd"], y=g["profit"], mode="markers+text", text=g["sub_category"], textposition="top center",
                               marker=dict(size=10, color=[ACC if p < 0 else GREY for p in g["profit"]]),
                               hovertemplate="%{text}<br>Discount $ %{x:$,.0f}<br>Profit %{y:$,.0f}<extra></extra>"))
    fig.add_hline(y=0, line_color=GRID)
    fig.update_xaxes(**usd_ticks(g["discount_usd"].min(), g["discount_usd"].max()))
    fig.update_yaxes(**usd_ticks(g["profit"].min(), g["profit"].max()))
    note(fig, worst["discount_usd"], worst["profit"], f"{worst['sub_category']}: {usd(worst['profit'])}", ay=40)
    return finish(fig, title, "Discount $ given away", "Profit ($)")


def heat(h, title):
    fig = go.Figure(go.Heatmap(z=h.values, x=list(h.columns), y=list(h.index), zmin=-60, zmax=60, text=h.round(0).fillna("").astype(str).values,
                               texttemplate="%{text}", colorscale=[[0, ACC], [0.5, "#F5F5F5"], [1, BLUE]],
                               colorbar_title="Margin %", hovertemplate="%{y}, %{x} off<br>Margin %{z:.1f}%<extra></extra>"))
    return finish(fig, title, "Discount band", "Region")


def monthly(m, title):
    fig = go.Figure()
    for col, name, c in [("sales", "Net sales", GREY), ("discount_usd", "Discount $ given away", ACC)]:
        fig.add_scatter(x=m["order_month"], y=m[col], name=name, line=dict(color=c, width=2), mode="lines",
                        hovertemplate="%{x|%b %Y}<br>" + name + " %{y:$,.0f}<extra></extra>")
    fig.update_yaxes(**usd_ticks(0, m[["sales", "discount_usd"]].max().max()))
    return finish(fig, title, "Month", "USD per month ($)")


def backtest(b, title):
    """Holdout MAE (months 43-48) per series: seasonal naive vs ETS, lower is better."""
    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=2, subplot_titles=list(SERIES.values()))
    for i, s in enumerate(SERIES, 1):
        d = b[b.series == s].sort_values("mae", ascending=False)
        fig.add_trace(go.Bar(x=d.model.map(MODEL), y=d.mae, text=d.mae.map(usd), textposition="outside", cliponaxis=False,
                             marker_color=[ACC if m != "snaive" else GREY for m in d.model], customdata=d[["mape_pct"]],
                             hovertemplate="%{x}<br>MAE %{y:$,.0f}<br>MAPE %{customdata[0]:.1f}%<extra></extra>"), row=1, col=i)
        fig.update_yaxes(**usd_ticks(0, d.mae.max()), row=1, col=i)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(showlegend=False)
    return finish(fig, title, None, "MAE on 6 held-out months ($)")


def forecast(hist, f, series, title):
    fig = go.Figure()
    fig.add_scatter(x=pd.concat([f.month, f.month[::-1]]), y=pd.concat([f.hi95, f.lo95[::-1]]), fill="toself", fillcolor=GRID, mode="lines",
                    line=dict(width=0), name="95% interval", hoverinfo="skip")
    fig.add_scatter(x=hist["order_month"], y=hist[series], name="Actual", mode="lines", line=dict(color=GREY, width=2),
                    hovertemplate="%{x|%b %Y}<br>Actual %{y:$,.0f}<extra></extra>")
    fig.add_scatter(x=f.month, y=f.point, name="Forecast", mode="lines", line=dict(color=ACC, width=2.5), customdata=f[["lo95", "hi95"]],
                    hovertemplate="%{x|%b %Y}<br>Forecast %{y:$,.0f}<br>95%: %{customdata[0]:$,.0f} to %{customdata[1]:$,.0f}<extra></extra>")
    fig.update_yaxes(**usd_ticks(min(f.lo95.min(), hist[series].min()), max(f.hi95.max(), hist[series].max())))
    return finish(fig, title, "Month", f"{SERIES[series]} per month ($)")


def scenario(summ, title):
    """Scenario, not a prediction: 6-month margin at current policy vs the 20% cap (low and high case)."""
    fig = go.Figure(go.Bar(x=summ.case, y=summ.margin_pct, text=summ.margin_pct.map("{:.1f}%".format), textposition="outside",
                           cliponaxis=False, marker_color=[GREY, ACC, ACC], customdata=summ[["profit", "sales"]],
                           hovertemplate="%{x}<br>Margin %{y:.1f}%<br>Profit %{customdata[0]:$,.0f} on sales %{customdata[1]:$,.0f}<extra></extra>"))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return finish(fig, title, "Scenario (Jan-Jun 2018)", "Margin (% of net sales)")


if __name__ == "__main__":
    assert usd(3304.5) == "$3,305" and usd(-2.5) == "-$3" and usd(3304.4) == "$3,304"
    assert [usdk(v) for v in (-20000, 0, 2500, 2450, 120000)] == ["-$20K", "$0", "$2.5K", "$2.5K", "$120K"]
    assert usd_ticks(-5000, 20000)["ticktext"] == ["-$5K", "$0", "$5K", "$10K", "$15K", "$20K"]
    print("charts ok")
