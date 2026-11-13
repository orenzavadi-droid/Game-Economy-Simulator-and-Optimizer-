-- Soft currency issued and spent, segmented by original player archetype.
SELECT scenario, persona,
       ROUND(SUM(CASE WHEN event_type='login_reward' THEN coin_delta ELSE 0 END),1) AS login_sources,
       ROUND(SUM(CASE WHEN event_type='quest_reward' THEN coin_delta ELSE 0 END),1) AS quest_sources,
       ROUND(-SUM(CASE WHEN event_type='upgrade_purchase' THEN coin_delta ELSE 0 END),1) AS upgrade_sinks,
       ROUND(-SUM(CASE WHEN event_type='cosmetic_purchase' THEN coin_delta ELSE 0 END),1) AS cosmetic_sinks,
       ROUND(SUM(coin_delta),1) AS net_flow
FROM events
GROUP BY scenario,persona
ORDER BY scenario,persona;
