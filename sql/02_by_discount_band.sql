-- Do deeper discounts buy more units and keep a margin, or just give margin away?
-- Per band: volume, profit, margin, loss-making lines, share of all discount dollars.
SELECT discount_band,
       count(*) AS lines,
       sum(quantity) AS units,
       round(avg(quantity), 2) AS avg_units_per_line,
       round(sum(sales), 0) AS sales,
       round(sum(profit), 0) AS profit,
       round(100 * sum(profit) / sum(sales), 1) AS margin_pct,
       round(sum(discount_usd), 0) AS discount_usd,
       round(count(*) FILTER (WHERE profit < 0)::DOUBLE / count(*), 4) AS loss_lines_share,
       round(sum(discount_usd) / sum(sum(discount_usd)) OVER (), 4) AS share_of_discount_usd
FROM 'data/clean/lines.parquet'
GROUP BY discount_band
ORDER BY min(discount);
