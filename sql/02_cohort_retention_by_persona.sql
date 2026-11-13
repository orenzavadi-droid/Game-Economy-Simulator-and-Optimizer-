-- Strict D1, D7, D30 activity, denominator = original simulated installs.
SELECT p.scenario, p.persona, COUNT(*) AS installs,
       ROUND(AVG(CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.scenario=p.scenario
                      AND e.player_id=p.player_id AND e.event_type='session_start' AND e.day=1)
                 THEN 1.0 ELSE 0 END),4) AS d1_retention,
       ROUND(AVG(CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.scenario=p.scenario
                      AND e.player_id=p.player_id AND e.event_type='session_start' AND e.day=7)
                 THEN 1.0 ELSE 0 END),4) AS d7_retention,
       ROUND(AVG(CASE WHEN EXISTS (SELECT 1 FROM events e WHERE e.scenario=p.scenario
                      AND e.player_id=p.player_id AND e.event_type='session_start' AND e.day=30)
                 THEN 1.0 ELSE 0 END),4) AS d30_retention
FROM players p
GROUP BY p.scenario, p.persona
ORDER BY p.scenario, p.persona;
