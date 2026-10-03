"""Static PNGs for the README (matplotlib, same palette as the dashboard). Run: python make_figures.py"""
import matplotlib
import matplotlib.dates
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ACC, GREY, TXT, GRID = "#D55E00", "#9E9E9E", "#4D4D4D", "#D9D9D9"
BANDS = ["0%", "1-20%", "21-40%", ">40%"]
plt.rcParams.update({"font.family": "sans-serif", "text.color": TXT, "axes.labelcolor": TXT, "xtick.color": TXT, "ytick.color": TXT,
                     "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "axes.axisbelow": True, "figure.dpi": 130})
o = lambda n: pd.read_csv(f"outputs/{n}.csv")
usdk = lambda x, _=None: f"${x / 1e3:,.0f}K"


def save(fig, name, title):
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.savefig(f"assets/{name}.png")
    plt.close(fig)


def bars(name, title, labels, vals, colors, fmt, ylabel):
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.bar(labels, vals, color=colors)
    ax.axhline(0, color=GRID)
    for i, v in enumerate(vals):
        ax.text(i, v, fmt(v), ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
    ax.set(xlabel="Discount band", ylabel=ylabel)
    ax.margins(y=0.15)
    save(fig, name, title)


df = pd.read_parquet("data/clean/lines.parquet")
base, disc = df[df.discount == 0].quantity.mean(), df[df.discount > 0].quantity.mean()
u = o("02_by_discount_band").set_index("discount_band").loc[BANDS]
bars("units_by_band", f"Discounted lines sell {disc:.2f} units vs {base:.2f} at full price", BANDS, u.avg_units_per_line,
     [GREY] * 4, "{:.2f}".format, "Units per line")
bars("margin_by_band", "Every discount band above 20% loses money", BANDS, u.margin_pct,
     [ACC if v < 0 else GREY for v in u.margin_pct], "{:.1f}%".format, "Margin (% of net sales)")

hist, b, fc, sm = o("07_monthly"), o("11_forecast_backtest"), o("12_forecast"), o("14_forecast_scenario_margin")
for d, c in [(hist, "order_month"), (fc, "month")]:
    d[c] = pd.to_datetime(d[c])
NAMES = {"sales": "Net sales", "profit": "Profit"}
LABEL = {"snaive": "Seasonal naive", "ets_add_notrend": "ETS (A,N,A)"}

fig, axs = plt.subplots(1, 2, figsize=(9, 4))
for ax, s in zip(axs, NAMES):
    d = b[b.series == s].sort_values("mae", ascending=False)
    ax.bar(d.model.map(LABEL), d.mae, color=[GREY if m == "snaive" else ACC for m in d.model])
    for i, v in enumerate(d.mae):
        ax.text(i, v, f"${v:,.0f}", ha="center", va="bottom")
    ax.yaxis.set_major_formatter(usdk)
    ax.set(title=NAMES[s], ylabel="MAE on 6 held-out months")
    ax.margins(y=0.15)
save(fig, "backtest", "ETS cuts 6-month holdout error vs seasonal naive")

fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for ax, s in zip(axs, NAMES):
    d = fc[fc.series == s]
    ax.fill_between(d.month, d.lo95, d.hi95, color=GRID, label="95% interval")
    ax.plot(hist.order_month, hist[s], color=GREY, label="Actual")
    ax.plot(d.month, d.point, color=ACC, lw=2, label="Forecast")
    ax.yaxis.set_major_formatter(usdk)
    ax.xaxis.set_major_locator(matplotlib.dates.YearLocator())
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    ax.set(title=f"{NAMES[s]}: Jan-Jun 2018 forecast {usdk(d.point.sum())}", ylabel="$ per month")
axs[0].legend(frameon=False, fontsize=8, loc="upper left")
save(fig, "forecast", "Six-month forecast with 95% prediction intervals")

fig, ax = plt.subplots(figsize=(6.5, 4))
ax.bar(sm.case, sm.margin_pct, color=[GREY, ACC, ACC])
for i, v in enumerate(sm.margin_pct):
    ax.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
ax.set(ylabel="Margin (% of net sales)", xlabel="Scenario (Jan-Jun 2018)")
ax.margins(y=0.15)
save(fig, "scenario", "Scenario, not a prediction: a 20% cap lifts 6-month margin")
