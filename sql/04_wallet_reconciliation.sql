-- Every player's balance must equal initial wallet plus all event deltas.
-- Returns all players to make the audit independently inspectable.
WITH movement AS (
  SELECT scenario, player_id, SUM(coin_delta) AS ledger_change
  FROM events GROUP BY scenario, player_id
)
SELECT p.scenario, p.player_id, p.persona, p.initial_wallet,
       COALESCE(m.ledger_change,0) AS event_delta,
       p.ending_wallet,
       ROUND(p.initial_wallet + COALESCE(m.ledger_change,0) - p.ending_wallet,8) AS wallet_difference
FROM players p
LEFT JOIN movement m ON p.scenario=m.scenario AND p.player_id=m.player_id
ORDER BY p.scenario,p.player_id;
