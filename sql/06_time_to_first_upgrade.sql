-- Players without upgrade remain in denominator (no implied survival analysis).
WITH first_upgrade AS (
   SELECT scenario,player_id,MIN(day) AS first_upgrade_day
   FROM events WHERE event_type='upgrade_purchase'
   GROUP BY scenario,player_id
)
SELECT p.scenario,p.persona,COUNT(*) AS installs,
       SUM(CASE WHEN f.first_upgrade_day IS NOT NULL THEN 1 ELSE 0 END) AS ever_upgraded,
       ROUND(AVG(f.first_upgrade_day),2) AS mean_first_upgrade_day_among_upgraders,
       ROUND(AVG(CASE WHEN f.first_upgrade_day<=7 THEN 1.0 ELSE 0 END),3) AS upgrade_by_day7_per_install
FROM players p LEFT JOIN first_upgrade f
 ON p.scenario=f.scenario AND p.player_id=f.player_id
GROUP BY p.scenario,p.persona
ORDER BY p.scenario,p.persona;
