-- Confounding check (Simpson): is the band pattern the same within each region?
SELECT region, discount_band,
       count(*) AS lines,
       round(avg(quantity), 2) AS avg_units_per_line,
       round(100 * sum(profit) / sum(sales), 1) AS margin_pct
FROM 'data/clean/lines.parquet'
GROUP BY ALL
ORDER BY region, min(discount);
