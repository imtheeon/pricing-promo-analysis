-- Sizing for the recommendations, per year (4 full years of data, 2014-2017).
-- Discounts show no clear volume lift (02, 04, stats_volume_model), so each scenario is bounded:
--   low  = every affected line is lost (customers walk away at the higher price): profit change = -profit
--   high = every affected line still sells at the new price: profit change = list price x discount removed
-- Reality sits between the two; the README states this assumption.
WITH l AS (SELECT * FROM 'data/clean/lines.parquet')
-- Rec 1: cap every discount at 20%
SELECT 'cap discounts above 20% at 20%' AS scenario,
       count(*) AS lines,
       round(-sum(profit) / 4, 0) AS low_usd_per_year,
       round(sum(gross_sales * (discount - 0.20)) / 4, 0) AS high_usd_per_year
FROM l WHERE discount > 0.20
UNION ALL
-- Rec 2: drop 1-20% discounts where the sub-category still loses money at that depth (from 08)
SELECT 'drop 1-20% discounts on Storage, Supplies, Tables', count(*),
       round(-sum(profit) / 4, 0),
       round(sum(discount_usd) / 4, 0)
FROM l WHERE discount_band = '1-20%' AND sub_category IN ('Storage', 'Supplies', 'Tables')
UNION ALL
-- Rec 3: the remaining 1-20% discounts are profitable in aggregate but show no clear lift.
-- Low case is 0: dropping profitable lines would cost money, so the floor is 'no change'.
SELECT 'test removing other 1-20% discounts', count(*),
       0,
       round(sum(discount_usd) / 4, 0)
FROM l WHERE discount_band = '1-20%' AND sub_category NOT IN ('Storage', 'Supplies', 'Tables');
