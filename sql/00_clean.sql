-- Build the clean lines table: one row per order line with pricing and promotion analysis.
-- Run by clean.py. Rows are only dropped if invalid (duplicate id, non-positive sales/quantity,
-- discount outside [0,1), ship_date < order_date); DATA_QUALITY.md logs how many hit each rule.
CREATE OR REPLACE TABLE lines AS
WITH parsed AS (
    SELECT
        "Row ID"                                        AS row_id,
        "Order ID"                                      AS order_id,
        "Order Date"                                    AS order_date,
        date_trunc('month', "Order Date")::DATE        AS order_month,
        "Ship Date"                                     AS ship_date,
        "Ship Mode"                                     AS ship_mode,
        "Customer ID"                                   AS customer_id,
        "Segment"                                       AS segment,
        "City"                                          AS city,
        "State"                                         AS state,
        "Region"                                        AS region,
        "Product ID"                                    AS product_id,
        "Category"                                      AS category,
        "Sub-Category"                                  AS sub_category,
        "Product Name"                                  AS product_name,
        "Sales"                                         AS sales,
        "Quantity"                                      AS quantity,
        "Discount"                                      AS discount,
        "Profit"                                        AS profit
    FROM raw
)
SELECT
    order_id,
    order_date,
    order_month,
    ship_date,
    ship_mode,
    customer_id,
    segment,
    city,
    state,
    region,
    product_id,
    category,
    sub_category,
    product_name,
    sales,
    quantity,
    discount,
    profit,
    -- Derived pricing fields
    ROUND(sales / (1 - discount), 2)                   AS gross_sales,
    ROUND(sales / (1 - discount) - sales, 2)           AS discount_usd,
    ROUND(sales - profit, 2)                           AS cost,
    CASE
        WHEN sales <= 0 THEN NULL
        ELSE ROUND(profit / sales * 100, 2)
    END                                                 AS margin_pct,
    ROUND(sales / quantity, 4)                         AS unit_net_price,
    -- Discount band classification
    CASE
        WHEN discount = 0 THEN '0%'
        WHEN discount <= 0.2 THEN '1-20%'
        WHEN discount <= 0.4 THEN '21-40%'
        ELSE '>40%'
    END                                                 AS discount_band
FROM parsed
WHERE row_id IS NOT NULL
  AND sales > 0
  AND quantity > 0
  AND discount >= 0 AND discount < 1
  AND ship_date >= order_date;
