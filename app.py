import pandas as pd
import plotly.express as px
import streamlit as st

BLUE, ORANGE, GRAY, DARK = "#2a6fb0", "#d9622b", "#9aa5b1", "#4b5563"  # profit, loss, 0% baseline, neutral
BANDS = ["0%", "1-20%", "21-40%", ">40%"]
st.set_page_config(page_title="Pricing & Promo Analysis", layout="wide")


@st.cache_data
def load():
    df = pd.read_parquet("data/clean/lines.parquet")
    df["order_month"] = pd.to_datetime(df["order_month"])
    df["discount_band"] = pd.Categorical(df["discount_band"], BANDS, ordered=True)
    return df


def margin(g, by):
    r = g.groupby(by, observed=True)[["profit", "sales"]].sum()
    return (r["profit"] / r["sales"] * 100).reset_index(name="margin")


def style(fig, x, y, **kw):
    fig.update_layout(xaxis_title=x, yaxis_title=y, margin=dict(t=20, b=10, l=10, r=10),
                      legend_title_text="", height=340, **kw)
    return fig


df = load()
st.title("Pricing & promo analysis")
st.caption("Superstore sample data, 2014-2017. A discounted line = on promotion; baseline = 0% discount.")

with st.sidebar:
    st.header("Filters")
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
if f.empty:
    st.warning("No order lines match these filters.")
    st.stop()

loss_share = f.loc[f["profit"] < 0, "discount_usd"].sum() / max(f["discount_usd"].sum(), 1) * 100
k = st.columns(5)
k[0].metric("Net sales", f"${f['sales'].sum() / 1e6:,.2f}M")
k[1].metric("Profit", f"${f['profit'].sum() / 1e3:,.0f}K")
k[2].metric("Margin", f"{f['profit'].sum() / f['sales'].sum() * 100:.1f}%")
k[3].metric("Discount $ given away", f"${f['discount_usd'].sum() / 1e3:,.0f}K",
            help="List-price revenue minus net sales")
k[4].metric("Discount $ on loss-making lines", f"{loss_share:.0f}%")

c1, c2 = st.columns(2)
with c1.container(border=True):
    st.subheader("Units per line by discount band")
    r = f.groupby("discount_band", observed=True)["quantity"].mean().reset_index()
    fig = px.bar(r, x="discount_band", y="quantity", text=r["quantity"].map("{:.2f}".format),
                 color="discount_band", color_discrete_map={"0%": GRAY, **{b: DARK for b in BANDS[1:]}})
    fig.update_layout(showlegend=False)
    st.plotly_chart(style(fig, "Discount band", "Units per line"), width="stretch")
    base, disc = f.loc[f["discount"] == 0, "quantity"].mean(), f.loc[f["discount"] > 0, "quantity"].mean()
    st.caption(f"Discounted lines average {disc:.2f} units vs {base:.2f} at 0% ({disc / base - 1:+.0%}) in this selection. "
               "Across the full data the same products sell the same units either way (README, finding 1)."
               if base == base and disc == disc else "This selection has no lines on one side of the comparison.")
with c2.container(border=True):
    st.subheader("Margin % by discount band")
    r = margin(f, "discount_band")
    fig = px.bar(r, x="discount_band", y="margin", text=r["margin"].map("{:.0f}%".format),
                 color=r["margin"].lt(0).map({True: "Loss", False: "Profit"}),
                 color_discrete_map={"Loss": ORANGE, "Profit": BLUE})
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(style(fig, "Discount band", "Margin (% of net sales)"), width="stretch")
    neg = r.loc[r["margin"] < 0, "discount_band"].astype(str).tolist()
    st.caption("Loss-making bands in this selection: " + (", ".join(neg) if neg else "none") + ".")

c3, c4 = st.columns(2)
with c3.container(border=True):
    st.subheader("Profit vs discount $ by sub-category")
    g = f.groupby("sub_category")[["profit", "discount_usd"]].sum().reset_index()
    fig = px.scatter(g, x="discount_usd", y="profit", text="sub_category",
                     color=g["profit"].lt(0).map({True: "Loss", False: "Profit"}),
                     color_discrete_map={"Loss": ORANGE, "Profit": BLUE})
    fig.update_traces(textposition="top center", marker_size=10)
    fig.add_hline(y=0, line_color=GRAY)
    fig.update_xaxes(tickprefix="$", tickformat=",.2s")
    fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    st.plotly_chart(style(fig, "Discount $ given away", "Profit"), width="stretch")
    worst = g.loc[g["profit"].idxmin()]
    usd = lambda v: f"-${-v:,.0f}" if v < 0 else f"${v:,.0f}"
    st.caption(f"Lowest-profit sub-category in this selection: {worst['sub_category']} "
               f"({usd(worst['profit'])} profit on {usd(worst['discount_usd'])} given away).")
with c4.container(border=True):
    st.subheader("Margin % by region and discount band")
    h = margin(f, ["region", "discount_band"]).pivot(index="region", columns="discount_band", values="margin")
    fig = px.imshow(h, text_auto=".0f", aspect="auto", zmin=-60, zmax=60, color_continuous_scale=[ORANGE, "#e5e7eb", BLUE])
    fig.update_layout(coloraxis_colorbar_title="Margin %")
    st.plotly_chart(style(fig, "Discount band", "Region"), width="stretch")
    deep = h.reindex(columns=["21-40%", ">40%"]).stack().dropna()
    st.caption(f"Orange = loss, blue = profit, scale capped at +/-60%. Above 20% discount, {(deep < 0).sum()} of {len(deep)} "
               "region cells in this selection lose money.")

with st.container(border=True):
    st.subheader("Monthly net sales and discount $")
    m = f.groupby("order_month")[["sales", "discount_usd"]].sum().reset_index()
    m = m.melt("order_month", var_name="s", value_name="usd")
    m["s"] = m["s"].map({"sales": "Net sales", "discount_usd": "Discount $ given away"})
    fig = px.line(m, x="order_month", y="usd", color="s", color_discrete_map={"Net sales": DARK, "Discount $ given away": GRAY})
    fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    st.plotly_chart(style(fig, "Month", "USD"), width="stretch")
    st.caption(f"Discount $ given away equals {f['discount_usd'].sum() / f['sales'].sum() * 100:.0f}% of net sales over the selected period.")

st.subheader("Keep / cut / redesign")
kc = pd.read_csv("outputs/08_keep_cut_redesign.csv")
colors = {"cut": ORANGE, "keep": BLUE, "redesign": GRAY}
st.dataframe(
    kc.style.map(lambda v: f"color: {colors.get(v, 'inherit')}; font-weight: bold", subset=["verdict"])
      .format({"lines": "{:,}", "profit": "${:,.0f}", "margin_pct": "{:.1f}%", "discount_usd": "${:,.0f}", "unit_lift": "{:+.1%}", "base_lines": "{:,.0f}"}),
    hide_index=True, width="stretch")
st.caption("Full data, ignores sidebar filters. Verdict rule: cut = margin <= 0; keep = profitable and unit lift above +5% "
           "vs a 0% baseline of 20+ lines; redesign = profitable but no clear lift. Even 'keep' lifts are unconfirmed: test before relying on them.")
