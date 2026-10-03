-- Monthly trend: do heavier-discount months sell more or earn less?
SELECT order_month,
       round(sum(sales), 0) AS sales,
       round(sum(profit), 0) AS profit,
       round(sum(discount_usd), 0) AS discount_usd,
       round(count(*) FILTER (WHERE discount > 0)::DOUBLE / count(*), 3) AS share_discounted,
       round(avg(discount), 3) AS avg_discount
FROM 'data/clean/lines.parquet'
GROUP BY order_month
ORDER BY order_month;
