-- Verdict per sub-category x discount band (non-0%, >=20 lines).
-- Rule: margin_pct <= 0 -> 'cut' (loses money);
--       profitable AND unit lift > +5% vs a 0% baseline cell of >= 20 lines -> 'keep';
--       otherwise 'redesign' (profitable, but no clear volume lift, or too thin a baseline to tell).
-- The 5% threshold keeps small, noisy lifts from earning a 'keep'.
WITH cell AS (
    SELECT sub_category, discount_band,
           count(*) AS lines,
           round(sum(profit), 0) AS profit,
           round(100 * sum(profit) / sum(sales), 1) AS margin_pct,
           round(sum(discount_usd), 0) AS discount_usd,
           avg(quantity) AS units_per_line
    FROM 'data/clean/lines.parquet'
    GROUP BY ALL
), base AS (
    SELECT *, max(units_per_line) FILTER (WHERE discount_band = '0%') OVER (PARTITION BY sub_category) AS base_units,
           max(lines) FILTER (WHERE discount_band = '0%') OVER (PARTITION BY sub_category) AS base_lines
    FROM cell
)
SELECT sub_category, discount_band, lines, base_lines, profit, margin_pct, discount_usd,
       round(units_per_line / base_units - 1, 3) AS unit_lift,
       CASE WHEN margin_pct <= 0 THEN 'cut'
            WHEN base_lines >= 20 AND units_per_line / base_units - 1 > 0.05 THEN 'keep'
            ELSE 'redesign' END AS verdict
FROM base
WHERE discount_band <> '0%' AND lines >= 20
ORDER BY verdict, profit;
