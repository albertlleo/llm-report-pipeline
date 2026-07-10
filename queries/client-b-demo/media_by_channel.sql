-- Media spend and performance metrics by channel
-- Source table is long-format (one row per metric per campaign).
-- Aggregated here server-side to avoid fetching hundreds of thousands of rows.
SELECT
  date,
  acme_channel_name AS channel,
  SUM(value)         AS spend -- we sum all the expense for the campaign for that channel
FROM `{project}.{dataset}.{table}`
WHERE
  date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY) -- yesterday + day before for Δ% computation
  AND date < CURRENT_DATE() -- exclude today in case it's incomplete
  AND metric = 'cost' -- we only want this metric, dont want to sun clicks, etc.
GROUP BY date, channel
HAVING SUM(value) > 0 -- avoiding channels with 0 expense since do not provide info
ORDER BY date DESC, spend DESC -- llm can see the more relevant channels
