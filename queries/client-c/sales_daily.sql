-- Daily sales data aggregated by date.
-- Table has one pre-aggregated row per date/store; SUM across stores gives totals.
-- Note: if `metric` acts as a row-type filter (like in media tables), add WHERE metric = '...'
SELECT
  date,
  SUM(orders)       AS orders,
  SUM(transactions) AS transactions,
  SUM(gross_sales)  AS gross_sales,
  SUM(net_sales)    AS net_sales,
  SUM(total_sales)  AS total_sales
FROM `{project}.{dataset}.{table}`
WHERE
  date >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 DAY)
  AND date < CURRENT_DATE()
GROUP BY date
ORDER BY date DESC
