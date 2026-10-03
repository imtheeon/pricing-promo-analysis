-- Is discounting a state-level policy? Per state: how often and how deep, and what margin results.
SELECT state,
       count(*) AS lines,
       round(count(*) FILTER (WHERE discount > 0)::DOUBLE / count(*), 3) AS share_discounted,
       round(avg(discount), 3) AS avg_discount,
       round(sum(sales), 0) AS sales,
       round(sum(profit), 0) AS profit,
       round(100 * sum(profit) / sum(sales), 1) AS margin_pct,
       round(sum(discount_usd), 0) AS discount_usd
FROM 'data/clean/lines.parquet'
GROUP BY state
ORDER BY discount_usd DESC, state;
