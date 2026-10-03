-- Is discounting a promotion decision or a geographic pricing policy?
-- Groups states by how often they discount: every line, some lines, or never.
WITH s AS (
    SELECT state, avg((discount > 0)::INT) AS share_discounted
    FROM 'data/clean/lines.parquet' GROUP BY state
)
SELECT CASE WHEN share_discounted = 1 THEN 'every line discounted'
            WHEN share_discounted = 0 THEN 'never discounts'
            ELSE 'discounts some lines' END AS state_policy,
       count(DISTINCT l.state) AS states,
       count(*) AS lines,
       round(avg(l.quantity), 2) AS avg_units_per_line,
       round(avg(l.discount), 3) AS avg_discount,
       round(sum(l.sales), 0) AS sales,
       round(sum(l.profit), 0) AS profit,
       round(sum(l.profit) / sum(l.sales) * 100, 1) AS margin_pct,
       round(sum(l.discount_usd), 0) AS discount_usd,
       round(sum(l.discount_usd) / sum(sum(l.discount_usd)) OVER (), 4) AS share_of_discount_usd
FROM 'data/clean/lines.parquet' l JOIN s USING (state)
GROUP BY 1
ORDER BY discount_usd DESC;
