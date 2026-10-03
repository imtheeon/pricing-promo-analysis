-- Same product sold at 0% and at a discount: units per line in each state (paired; analyze.py summarises).
SELECT product_id,
       any_value(sub_category) AS sub_category,
       avg(quantity) FILTER (WHERE discount = 0) AS units_full,
       avg(quantity) FILTER (WHERE discount > 0) AS units_disc,
       count(*) FILTER (WHERE discount = 0) AS n_full,
       count(*) FILTER (WHERE discount > 0) AS n_disc
FROM 'data/clean/lines.parquet'
GROUP BY product_id
HAVING n_full > 0 AND n_disc > 0
ORDER BY product_id;
