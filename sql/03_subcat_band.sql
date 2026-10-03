-- Does a discount lift units in each sub-category, and at what margin?
-- unit_lift = avg units/line in band / the sub-category's 0% avg units/line - 1. Cells with >=20 lines only.
WITH cell AS (
    SELECT category, sub_category, discount_band,
           count(*) AS lines,
           round(avg(quantity), 2) AS avg_units_per_line,
           round(sum(sales), 0) AS sales,
           round(sum(profit), 0) AS profit,
           round(100 * sum(profit) / sum(sales), 1) AS margin_pct,
           round(sum(discount_usd), 0) AS discount_usd
    FROM 'data/clean/lines.parquet'
    GROUP BY ALL
), base AS (
    SELECT *,
           max(avg_units_per_line) FILTER (WHERE discount_band = '0%') OVER (PARTITION BY sub_category) AS base_units_per_line,
           max(margin_pct) FILTER (WHERE discount_band = '0%') OVER (PARTITION BY sub_category) AS base_margin_pct
    FROM cell
)
SELECT *, round(avg_units_per_line / base_units_per_line - 1, 3) AS unit_lift
FROM base
WHERE lines >= 20
ORDER BY category, sub_category, discount_band;
