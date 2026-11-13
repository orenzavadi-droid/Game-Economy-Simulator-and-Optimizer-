-- Per-original-install progression and optional purchases.
SELECT scenario, persona, COUNT(*) AS installs,
       ROUND(AVG(upgrades_total),3) AS upgrades_per_install,
       ROUND(AVG(cosmetics_total),3) AS cosmetics_per_install,
       ROUND(AVG(active_days),2) AS active_days_per_install,
       ROUND(AVG(ending_wallet),2) AS mean_ending_wallet_all_installs,
       ROUND(AVG(CASE WHEN alive_day_end=1 THEN ending_wallet ELSE NULL END),2) AS mean_wallet_survivors
FROM players
GROUP BY scenario, persona
ORDER BY scenario, persona;
