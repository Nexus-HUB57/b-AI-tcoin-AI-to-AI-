import { query } from "../db.js";
import { logger } from "../logger.js";

const TIER_THRESHOLDS = { new: 0, bronze: 0.4, silver: 0.7, gold: 0.85, platinum: 0.95 };

class ReputationEngine {
  async get(agentId) {
    const { rows } = await query(`SELECT * FROM agent_reputation WHERE agent_id = $1`, [agentId]);
    return rows[0] ?? null;
  }

  async record({ agentId, event, weight = 1.0, detail = {} }) {
    await query(
      `INSERT INTO reputation_events (agent_id, event, weight, detail) VALUES ($1,$2,$3,$4)`,
      [agentId, event, weight, JSON.stringify(detail)]
    );
    const { rows: agg } = await query(
      `SELECT
         COUNT(*) FILTER (WHERE event='trade_settled')::int AS settled,
         COUNT(*) FILTER (WHERE event='dispute_lost')::int AS disputes,
         COALESCE(SUM(CASE WHEN event='trade_settled' THEN (detail->>'volume')::numeric ELSE 0 END), 0)::numeric AS volume
       FROM reputation_events WHERE agent_id=$1`, [agentId]
    );
    const { settled, disputes, volume } = agg[0];
    const uptime = Math.max(0, 1.0 - (disputes / 50));
    const score =
      Math.min(settled / 100, 1.0) * 0.5 +
      uptime * 0.3 +
      Math.min(Math.log10(Math.max(Number(volume), 1)) / 6, 1.0) * 0.2;
    let tier = "new";
    for (const [t, th] of Object.entries(TIER_THRESHOLDS)) { if (score >= th) tier = t; }

    await query(
      `INSERT INTO agent_reputation
         (agent_id, trades_settled, trades_disputed, volume_total, uptime_score, trust_tier, last_updated)
       VALUES ($1,$2,$3,$4,$5,$6,now())
       ON CONFLICT (agent_id) DO UPDATE SET
         trades_settled = EXCLUDED.trades_settled, trades_disputed = EXCLUDED.trades_disputed,
         volume_total = EXCLUDED.volume_total, uptime_score = EXCLUDED.uptime_score,
         trust_tier = EXCLUDED.trust_tier, last_updated = now()`,
      [agentId, settled, disputes, volume, uptime, tier]
    );
    logger.debug({ agentId, event, tier, score: score.toFixed(3) }, "reputation: registrado");
    return { tier, score };
  }

  async setTier(agentId, tier, tradesSettled = 0) {
    await query(
      `UPDATE agent_reputation SET trust_tier=$2, trades_settled=$3, last_updated=now() WHERE agent_id=$1`,
      [agentId, tier, tradesSettled]
    );
  }
}

export const reputation = new ReputationEngine();
