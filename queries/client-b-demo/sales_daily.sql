-- Daily sales data for the last 8 days, aggregated to one row per date.
-- Source table is product-level (one row per order-product combination).
-- orders uses COUNT(DISTINCT order_id) to avoid double-counting multi-product orders.
-- Financial metrics are summed at product level (correct — each row holds product share).
SELECT
  date,
  COUNT(DISTINCT order_id)                                  AS orders,
  COUNT(DISTINCT CASE WHEN is_new_customer = 1
                      THEN order_id END)                    AS new_customer_orders,
  SUM(gross_sales)                                          AS gross_sales,
  SUM(net_sales)                                            AS net_sales,
  SUM(total_sales)                                          AS total_sales,
  SUM(discounts)                                            AS discounts,
  SUM(returns)                                              AS returns,
  SUM(shipping)                                             AS shipping,
  SUM(tax)                                                  AS tax,
  SUM(ordered_quantity)                                     AS ordered_quantity
FROM `{project}.{dataset}.{table}`
WHERE
  date >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 DAY)
  AND date < CURRENT_DATE()
GROUP BY date
ORDER BY date DESC
