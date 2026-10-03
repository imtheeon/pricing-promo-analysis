import pandas as pd
import streamlit as st

import charts as C

st.set_page_config(page_title="Pricing & Promo Analysis", layout="wide")

BOTTOM_LINE = ("Discounts here do not sell more units: the same product sells 3.80 units per line at full price and 3.82 when discounted. "
               "That means the **$567K of discounts over four years is mostly margin given away**, and every discount band above 20% loses money. "
               "Capping discounts at 20% would add an estimated **$34K-$55K of profit a year**, against today's $72K a year. "
               "Test the remaining small discounts before keeping them.")


@st.cache_data
def load():
    df = pd.read_parquet("data/clean/lines.parquet")
    df["order_month"] = pd.to_datetime(df["order_month"])
    df["discount_band"] = pd.Categorical(df["discount_band"], C.BANDS, ordered=True)
    out = {n: pd.read_csv(f"outputs/{n}.csv") for n in ["07_monthly", "11_forecast_backtest", "12_forecast", "14_forecast_scenario_margin"]}
    out["07_monthly"]["order_month"] = pd.to_datetime(out["07_monthly"]["order_month"])
    out["12_forecast"]["month"] = pd.to_datetime(out["12_forecast"]["month"])
    return df, out


def margin(g, by):
    r = g.groupby(by, observed=True)[["profit", "sales"]].sum()
    return (r["profit"] / r["sales"] * 100).reset_index(name="margin")


esc = lambda s: s.replace("$", r"\$")  # st markdown treats $...$ as LaTeX


def show(fig, caption):
    st.plotly_chart(fig, width="stretch")
    st.caption(esc("So what: " + caption))


df, out = load()
st.title("Pricing & promo analysis")
st.caption("Superstore sample data, 2014-2017: which discounts raise sales and profit, and which just give away margin?")
st.info("**Bottom line.** " + esc(BOTTOM_LINE))

with st.sidebar:
    st.header("Filters")
    st.caption("Apply to the Pricing tab. The Forecast tab always uses all data.")
    reg = st.multiselect("Region", sorted(df["region"].unique()))
    cat = st.multiselect("Category", sorted(df["category"].unique()))
    sub = st.multiselect("Sub-category", sorted(df["sub_category"].unique()))
    months = sorted(df["order_month"].unique())
    lo, hi = st.select_slider("Order month", months, value=(months[0], months[-1]),
                              format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"))

f = df[df["order_month"].between(lo, hi)]
for col, sel in [("region", reg), ("category", cat), ("sub_category", sub)]:
    if sel:
        f = f[f[col].isin(sel)]

tab_p, tab_f = st.tabs(["Pricing", "Forecast"])

with tab_p:
    if f.empty:
        st.info("No rows match these filters.")
    else:
        base, disc = f.loc[f["discount"] == 0, "quantity"].mean(), f.loc[f["discount"] > 0, "quantity"].mean()
        m0, m40 = f.loc[f["discount"] == 0], f.loc[f["discount"] > 0.2]
        mg = lambda g: g["profit"].sum() / g["sales"].sum() * 100 if len(g) else float("nan")
        loss_share = f.loc[f["profit"] < 0, "discount_usd"].sum() / max(f["discount_usd"].sum(), 1) * 100
        k = st.columns(4)
        k[0].metric("Units per line, discounted", f"{disc:.2f}", f"{disc - base:+.2f} vs {base:.2f} at full price", delta_color="off")
        k[1].metric("Margin, lines >20% off", f"{mg(m40):.1f}%", f"{mg(m40) - mg(m0):+.1f} pts vs {mg(m0):.1f}% at 0% off")
        k[2].metric("Discount $ given away", f"${f['discount_usd'].sum() / 1e3:,.0f}K",
                    f"{f['discount_usd'].sum() / f['sales'].sum() * 100:.0f}% of net sales", delta_color="off",
                    help="List-price revenue minus net sales (net sales = Sales as recorded, after discount)")
        k[3].metric("Discount $ on loss-making lines", f"{loss_share:.0f}%",
                    esc(f"profit ${f['profit'].sum() / 1e3:,.0f}K on net sales ${f['sales'].sum() / 1e6:,.2f}M"), delta_color="off")
        st.write("")

        c1, c2 = st.columns(2)
        with c1:
            r = f.groupby("discount_band", observed=True)["quantity"].mean().reset_index()
            show(C.bars(r, "discount_band", "quantity", None, f"Discounted lines sell {disc:.2f} units vs {base:.2f} at full price",
                        "Discount band", "Units per line", "{:.2f}".format, "%{x} off<br>%{y:.2f} units per line"),
                 "deeper discounts do not buy bigger baskets (README, finding 1).")
        with c2:
            r = margin(f, "discount_band")
            neg = r.loc[r["margin"] < 0, "discount_band"].astype(str).tolist()
            fig = C.bars(r, "discount_band", "margin", None, "Every band above 20% off loses money" if neg else "No band loses money in this selection",
                         "Discount band", "Margin (% of net sales)", "{:.0f}%".format, "%{x} off<br>Margin %{y:.1f}%")
            fig.update_traces(marker_color=[C.ACC if v < 0 else C.GREY for v in r["margin"]])
            fig.update_yaxes(ticksuffix="%")
            show(fig, "loss-making bands: " + (", ".join(neg) if neg else "none") + ".")

        c3, c4 = st.columns(2)
        with c3:
            g = f.groupby("sub_category")[["profit", "discount_usd"]].sum().reset_index()
            w = g.loc[g["profit"].idxmin()]
            show(C.subcat(g, f"{w['sub_category']} loses the most: {C.usd(w['profit'])} on {C.usd(w['discount_usd'])} of discounts"),
                 "sub-categories that give away the most discount $ are not the ones that earn the most.")
        with c4:
            h = margin(f, ["region", "discount_band"]).pivot(index="region", columns="discount_band", values="margin")
            deep = h.reindex(columns=["21-40%", ">40%"]).stack().dropna()
            show(C.heat(h, f"{(deep < 0).sum()} of {len(deep)} region cells above 20% off lose money"),
                 "orange = loss, blue = profit, scale capped at +/-60%. The pattern holds in every region.")

        m = f.groupby("order_month")[["sales", "discount_usd"]].sum().reset_index()
        show(C.monthly(m, f"Discounts equal {f['discount_usd'].sum() / f['sales'].sum() * 100:.0f}% of net sales over the period"),
             "discount spend rises with sales peaks, but the peaks do not earn proportionally more profit.")

        st.subheader("Keep / cut / redesign")
        kc = pd.read_csv("outputs/08_keep_cut_redesign.csv")
        colors = {"cut": C.ACC, "keep": C.BLUE, "redesign": C.GREY}
        st.dataframe(
            kc.style.map(lambda v: f"color: {colors.get(v, 'inherit')}; font-weight: bold", subset=["verdict"])
              .format({"lines": "{:,}", "profit": "${:,.0f}", "margin_pct": "{:.1f}%", "discount_usd": "${:,.0f}",
                       "unit_lift": "{:+.1%}", "base_lines": "{:,.0f}"}),
            hide_index=True, width="stretch")
        st.caption("Full data, ignores sidebar filters. Cut = margin <= 0; keep = profitable with unit lift above +5% vs a 0% baseline of 20+ lines; "
                   "redesign = profitable but no clear lift. Even 'keep' lifts are unconfirmed: test before relying on them.")

with tab_f:
    hist, b, fc, sm = out["07_monthly"], out["11_forecast_backtest"], out["12_forecast"], out["14_forecast_scenario_margin"]
    st.caption("48 months of history, forecast for the next 6 months (Jan-Jun 2018) with a 95% prediction interval. Only four years of a public "
               "sample dataset; the forecast is not a promise, and the interval understates model uncertainty.")
    r1 = st.columns(2)
    for col, s in zip(r1, C.SERIES):
        d = fc[fc.series == s]
        with col:
            show(C.forecast(hist, d, s, f"{C.SERIES[s]} Jan-Jun 2018: {C.usd(d.point.sum())} forecast"),
                 f"model: {C.MODEL[d.model.iloc[0]]}; grey band = 95% prediction interval.")
    r2 = st.columns(2)
    with r2[0]:
        show(C.backtest(b, "ETS cuts holdout error vs seasonal naive for both series"),
             "fit on months 1-42, forecast months 43-48. Profit MAPE is unstable (near-zero months), so MAE is the yardstick.")
    with r2[1]:
        base, lo_, hi_ = sm.margin_pct
        st.caption("SCENARIO, NOT A PREDICTION")
        show(C.scenario(sm, f"A 20% cap would lift 6-month margin from {base:.1f}% to about {min(lo_, hi_):.0f}%"),
             "cap sizing reuses the sql/09 low and high cases (outputs/09), applied to the forecast by calendar month.")
    t = b.assign(model=b.model.map(C.MODEL))
    st.dataframe(t[["series", "model", "mae", "mape_pct", "smape_pct", "mae_vs_snaive_pct"]], hide_index=True, width="stretch",
                 column_config={"mae": st.column_config.NumberColumn("MAE ($)", format="$%,.0f"),
                                "mape_pct": st.column_config.NumberColumn("MAPE", format="%.1f%%"),
                                "smape_pct": st.column_config.NumberColumn("sMAPE", format="%.1f%%"),
                                "mae_vs_snaive_pct": st.column_config.NumberColumn("MAE vs naive", format="%+.1f%%")})
    st.caption("Holdout backtest of 6 months. Profit MAPE is inflated by near-zero months, so compare MAE.")
