-- Event ledger: income vs spending by scenario and day.
SELECT scenario, day,
       ROUND(SUM(CASE WHEN coin_delta > 0 THEN coin_delta ELSE 0 END),2) AS currency_sources,
       ROUND(-SUM(CASE WHEN coin_delta < 0 THEN coin_delta ELSE 0 END),2) AS currency_sinks,
       ROUND(SUM(coin_delta),2) AS net_issuance,
       COUNT(CASE WHEN event_type = 'session_start' THEN 1 END) AS sessions,
       COUNT(CASE WHEN event_type = 'upgrade_purchase' THEN 1 END) AS upgrades
FROM events
GROUP BY scenario, day
ORDER BY scenario, day;
