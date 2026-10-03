"""6-month forecast (Jan-Jun 2018) of monthly net sales and profit, plus a discount-cap margin scenario.
Input: outputs/07_monthly.csv (net sales = Sales as recorded, already after discount).
Outputs: 11_forecast_backtest.csv, 12_forecast.csv, 13_forecast_scenario.csv, 14_forecast_scenario_margin.csv."""
import warnings
import duckdb
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

warnings.filterwarnings('ignore')
H, M, N_SIM, SEED, Z95 = 6, 12, 5000, 0, norm.ppf(.975)
m = pd.read_csv('outputs/07_monthly.csv', parse_dates=['order_month']).set_index('order_month')
m.index.freq = 'MS'
assert len(m) == 48
SERIES = {'sales': m['sales'], 'profit': m['profit']}


def snaive(y, h):
    """Point = value 12 months earlier. 95% half-width = z * sd(seasonal differences) (all h <= 12, so no horizon scaling)."""
    pt = np.array([y.iloc[len(y) - M + i] for i in range(h)])
    return pt, Z95 * (y - y.shift(M)).dropna().std()


def ets(y, h):
    """ETS(A,N,A): additive error, no trend, additive seasonality (additive for both series: profit has negative months)."""
    res = ETSModel(y, error='add', trend=None, seasonal='add', seasonal_periods=M).fit(disp=False)
    return res.forecast(h).to_numpy(), res


def backtest():
    """Hold out the last 6 months: fit on months 1-42, forecast months 43-48."""
    rows = []
    for name, y in SERIES.items():
        train, test = y.iloc[:-H], y.iloc[-H:]
        assert len(train) == 42 and train.index.max() < test.index.min()
        for mod, f in [('snaive', snaive(train, H)[0]), ('ets_add_notrend', ets(train, H)[0])]:
            ae = (test.to_numpy() - f)
            rows.append({'series': name, 'model': mod, 'n_forecasts': H, 'mae': np.abs(ae).mean(),
                         'mape_pct': (np.abs(ae) / np.abs(test.to_numpy())).mean() * 100,
                         'smape_pct': (2 * np.abs(ae) / (np.abs(test.to_numpy()) + np.abs(f))).mean() * 100})
    b = pd.DataFrame(rows)
    base = b[b.model == 'snaive'].set_index('series').mae
    b['mae_vs_snaive_pct'] = [(r.mae / base[r.series] - 1) * 100 for r in b.itertuples()]
    return b


def final_forecast(name, y, b):
    """Use ETS only if its holdout MAE beats seasonal naive; else the baseline."""
    r = b[b.series == name].set_index('model')
    mod = 'ets_add_notrend' if r.mae['ets_add_notrend'] < r.mae['snaive'] else 'snaive'
    idx = pd.date_range(y.index[-1] + pd.offsets.MonthBegin(), periods=H, freq='MS')
    if mod == 'snaive':
        pt, hw = snaive(y, H)
        lo, hi = pt - hw, pt + hw
    else:
        pt, res = ets(y, H)
        sims = res.simulate(H, repetitions=N_SIM, anchor='end', rng=np.random.default_rng(SEED)).to_numpy()
        lo, hi = np.quantile(sims, [.025, .975], axis=1)
    return pd.DataFrame({'series': name, 'month': idx, 'model': mod, 'point': pt, 'lo95': lo, 'hi95': hi})


def scenario(f):
    """Cap discounts above 20% at 20%, same logic as sql/09 row 1, by calendar month (annual = 4-year total / 4):
    low  = every affected line is lost: profit change = -profit, net sales change = -sales
    high = every affected line still sells at 20% off: profit and net sales change = gross_sales * (discount - 0.20)."""
    a = duckdb.sql("""SELECT month(order_month) AS mo, -sum(profit) / 4 AS p_low, -sum(sales) / 4 AS s_low,
                             sum(gross_sales * (discount - 0.20)) / 4 AS p_high
                      FROM 'data/clean/lines.parquet' WHERE discount > 0.20 GROUP BY 1 ORDER BY 1""").df().set_index('mo')
    ref = pd.read_csv('outputs/09_impact_scenarios.csv').iloc[0]
    assert abs(a.p_low.sum() - ref.low_usd_per_year) <= 1 and abs(a.p_high.sum() - ref.high_usd_per_year) <= 1
    s = f[f.series == 'sales'].set_index('month').point.rename('sales_no_cap').to_frame()
    s['profit_no_cap'] = f[f.series == 'profit'].set_index('month').point
    mo = s.index.month
    s['profit_cap_low'], s['profit_cap_high'] = s.profit_no_cap + a.p_low[mo].to_numpy(), s.profit_no_cap + a.p_high[mo].to_numpy()
    s['sales_cap_low'], s['sales_cap_high'] = s.sales_no_cap + a.s_low[mo].to_numpy(), s.sales_no_cap + a.p_high[mo].to_numpy()
    t = s.sum()
    summ = pd.DataFrame([{'case': c, 'sales': t[f'sales_{k}'], 'profit': t[f'profit_{k}'],
                          'margin_pct': t[f'profit_{k}'] / t[f'sales_{k}'] * 100}
                         for c, k in [('current policy', 'no_cap'), ('20% cap, low case', 'cap_low'), ('20% cap, high case', 'cap_high')]])
    return s.reset_index(), summ


def check(b, f, s):
    assert (f.lo95 <= f.point).all() and (f.point <= f.hi95).all()
    y = SERIES['sales']
    y2 = y.copy()
    y2.iloc[42:] = 1e9  # changing the held-out months must not change the backtest forecast
    assert np.allclose(snaive(y.iloc[:42], H)[0], snaive(y2.iloc[:42], H)[0]) and np.allclose(ets(y.iloc[:42], H)[0], ets(y2.iloc[:42], H)[0])


if __name__ == '__main__':
    b = backtest()
    f = pd.concat([final_forecast(n, SERIES[n], b) for n in SERIES], ignore_index=True)
    sc, summ = scenario(f)
    check(b, f, sc)
    for df, p in [(b, '11_forecast_backtest'), (f, '12_forecast'), (sc, '13_forecast_scenario'), (summ, '14_forecast_scenario_margin')]:
        num = df.select_dtypes('number').columns
        df[num] = df[num].round(1)
        df.to_csv(f'outputs/{p}.csv', index=False)
        print(f'\n== {p}\n{df.to_string(index=False)}')
