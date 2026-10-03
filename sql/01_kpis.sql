-- Headline KPIs: volume, revenue, margin given away, and how much discount landed on loss-making lines.
-- Discounted line = discount > 0. margin = profit / net sales.
SELECT count(*) AS lines,
       count(DISTINCT order_id) AS orders,
       sum(quantity) AS units,
       round(sum(gross_sales), 0) AS gross_sales,
       round(sum(sales), 0) AS sales,
       round(sum(discount_usd), 0) AS discount_usd,
       round(sum(profit), 0) AS profit,
       round(sum(profit) / sum(sales), 4) AS margin,
       round(count(*) FILTER (WHERE discount > 0)::DOUBLE / count(*), 4) AS share_lines_discounted,
       round(sum(discount_usd) FILTER (WHERE profit < 0) / sum(discount_usd), 4) AS share_discount_usd_on_loss_lines
FROM 'data/clean/lines.parquet';
