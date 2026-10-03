import duckdb, glob, os
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import t, wilcoxon

os.makedirs('outputs', exist_ok=True)
r = {}
for f in sorted(glob.glob('sql/[01][0-9]_*.sql')):
    if f.endswith('00_clean.sql'):
        continue
    stem = os.path.basename(f)[:-4]
    r[stem] = duckdb.sql(open(f, encoding='utf-8').read()).df()
    r[stem].to_csv(f'outputs/{stem}.csv', index=False)
    print(f'\n== {stem}\n{r[stem].to_string(index=False)}')
assert abs(r['02_by_discount_band'].sales.sum() - r['01_kpis'].sales[0]) <= 2  # per-band rounding

# (a) paired product lift: same product, discounted vs full price. Mean paired difference in units
# per line (t CI) and ratio of the two product-level means - 1; a mean of per-product ratios is
# biased upward when most products have only a few lines per side.
p = r['04_product_paired_lift']
diff = p.units_disc - p.units_full
lo, hi = t.interval(.95, len(diff) - 1, diff.mean(), diff.sem())
s = pd.DataFrame([{'n_products': len(p), 'units_full': p.units_full.mean(), 'units_disc': p.units_disc.mean(),
                   'mean_diff_units': diff.mean(), 'ci_lo': lo, 'ci_hi': hi,
                   'ratio_of_means_lift': p.units_disc.mean() / p.units_full.mean() - 1,
                   'wilcoxon_p': wilcoxon(p.units_disc, p.units_full).pvalue}])
s.to_csv('outputs/stats_lift.csv', index=False)
print('\n== stats_lift\n', s.to_string(index=False))

# (b) band effects net of mix. Discounts are set by state, so SEs are clustered by state.
# 'within state' adds state fixed effects: only the 17 states that discount some lines but not
# others identify the effect, which removes the state-level confounder.
df = duckdb.sql("SELECT * FROM 'data/clean/lines.parquet'").df()
rows = []
specs = {'mix controls': 'C(sub_category) + C(region) + C(segment)',
         'within state': 'C(sub_category) + C(segment) + C(state)'}
for (spec, rhs), y in [(sp, y) for sp in specs.items() for y in ['quantity', 'profit']]:
    res = smf.ols(f"{y} ~ C(discount_band, Treatment('0%')) + {rhs}", df).fit(cov_type='cluster', cov_kwds={'groups': df['state']})
    ci = res.conf_int()
    for k in res.params.index[res.params.index.str.contains('discount_band')]:
        rows.append({'spec': spec, 'outcome': y, 'band': k.split('T.')[1].rstrip(']'), 'coef': res.params[k],
                     'ci_lo': ci.loc[k, 0], 'ci_hi': ci.loc[k, 1], 'p': res.pvalues[k]})
v = pd.DataFrame(rows)
v.to_csv('outputs/stats_volume_model.csv', index=False)
print('\n== stats_volume_model\n', v.to_string(index=False))
