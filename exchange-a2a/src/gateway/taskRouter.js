import crypto from "node:crypto";
import { query } from "../db.js";
import { orderBook } from "../matching/orderBook.js";
import { agentCard } from "../identity/agentCard.js";
import { logger } from "../logger.js";

class TaskRouter {
  async dispatch(method, params, ctx) {
    switch (method) {
      case "agent/card": return this.#handleCard(params);
      case "message/send": return this.#handleMessage(params, ctx);
      case "tasks/get": return this.#handleTaskGet(params);
      case "tasks/cancel": return this.#handleTaskCancel(params, ctx);
      default: throw Object.assign(new Error(`método desconhecido: ${method}`), { code: -32601 });
    }
  }
  async #handleCard({ agentId }) { return agentCard.wellKnown(agentId); }
  async #handleMessage({ message, contextId }, ctx) {
    const { intent, payload } = message ?? {};
    if (!intent) throw new Error("message.intent obrigatório");
    const taskId = `task-${crypto.randomUUID()}`;
    await query(`INSERT INTO a2a_tasks (task_id, agent_id, context_id, intent, payload, state) VALUES ($1,$2,$3,$4,$5,'submitted')`,
      [taskId, ctx.agentId, contextId ?? null, intent, JSON.stringify(payload ?? {})]);
    try {
      let result;
      switch (intent) {
        case "place_order": result = await orderBook.place({ ...payload, agentId: ctx.agentId, a2aTaskId: taskId }); break;
        case "cancel_order": result = await orderBook.cancel({ ...payload, agentId: ctx.agentId }); break;
        case "get_depth": result = await orderBook.depth(payload.pair); break;
        case "get_ticker": result = await orderBook.ticker(payload.pair); break;
        case "get_trades": result = await orderBook.recentTrades(payload.pair, payload.limit ?? 50); break;
        // P9: A2A pricing intents — agents publish and query service pricing tables
        case "publish_pricing": result = await this.#handlePublishPricing(payload, ctx.agentId); break;
        case "get_pricing": result = await this.#handleGetPricing(payload); break;
        case "deprecate_pricing": result = await this.#handleDeprecatePricing(payload, ctx.agentId); break;
        default: throw new Error(`intent desconhecido: ${intent}`);
      }
      await query(`UPDATE a2a_tasks SET state='completed', result=$2, completed_at=now() WHERE task_id=$1`, [taskId, JSON.stringify(result)]);
      return { taskId, state: "completed", result };
    } catch (err) {
      await query(`UPDATE a2a_tasks SET state='failed', error=$2, completed_at=now() WHERE task_id=$1`, [taskId, err.message]);
      logger.warn({ intent, err: err.message }, "task falhou");
      throw err;
    }
  }
  async #handleTaskGet({ taskId }) {
    const { rows } = await query(`SELECT task_id, state, result, error FROM a2a_tasks WHERE task_id=$1`, [taskId]);
    if (rows.length === 0) throw new Error("task não encontrada");
    return rows[0];
  }
  async #handleTaskCancel({ taskId }, ctx) {
    const { rowCount } = await query(`UPDATE a2a_tasks SET state='cancelled' WHERE task_id=$1 AND agent_id=$2 AND state IN ('submitted','working')`, [taskId, ctx.agentId]);
    if (rowCount === 0) throw new Error("task não cancelável");
    return { taskId, state: "cancelled" };
  }

  // P9: Publish pricing table for an agent's services in BAIT
  async #handlePublishPricing({ services }, agentId) {
    if (!Array.isArray(services) || services.length === 0) throw new Error("services array required");
    const results = [];
    for (const svc of services) {
      if (!svc.name || !svc.category || typeof svc.price_per_call_sats !== "number") {
        throw new Error("each service requires name, category, price_per_call_sats");
      }
      const { rows } = await query(
        `INSERT INTO a2a_service_listings (agent_id, service_name, category, price_per_call_sats, price_unit, description, min_commitment_sats, max_commitment_sats)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         ON CONFLICT (agent_id, service_name) DO UPDATE SET
           category=EXCLUDED.category, price_per_call_sats=EXCLUDED.price_per_call_sats,
           price_unit=EXCLUDED.price_unit, description=EXCLUDED.description,
           min_commitment_sats=EXCLUDED.min_commitment_sats, max_commitment_sats=EXCLUDED.max_commitment_sats,
           availability='available', updated_at=now()
         RETURNING service_name, category, price_per_call_sats, price_unit`,
        [agentId, svc.name, svc.category, svc.price_per_call_sats, svc.unit ?? "BAIT", svc.description ?? null, svc.min_commitment_sats ?? 0, svc.max_commitment_sats ?? null]
      );
      results.push(rows[0]);
      await query(`INSERT INTO pricing_audit_log (agent_id, action, service_name, new_price_sats) VALUES ($1,'publish',$2,$3)`, [agentId, svc.name, svc.price_per_call_sats]);
    }
    // Update agent pricing JSONB column
    await query(`UPDATE a2a_agents SET pricing=jsonb_build_object('services',$1::jsonb), pricing_updated_at=now() WHERE agent_id=$2`, [JSON.stringify(services), agentId]);
    logger.info({ agentId, count: results.length }, "pricing published");
    return { published: results };
  }

  // P9: Query pricing tables across agents (with filters)
  async #handleGetPricing({ category, max_price_sats, agent_id, limit } = {}) {
    const l = Math.min(limit ?? 50, 200);
    let sql, params;
    if (agent_id) {
      sql = `SELECT sl.agent_id, sl.service_name, sl.category, sl.price_per_call_sats, sl.price_unit, sl.description, sl.availability, sl.success_rate, sl.total_calls, a.moltbook_handle
             FROM a2a_service_listings sl JOIN a2a_agents a ON sl.agent_id=a.agent_id
             WHERE sl.agent_id=$1 AND sl.availability='available' ORDER BY sl.price_per_call_sats LIMIT $2`;
      params = [agent_id, l];
    } else if (category) {
      const maxPrice = max_price_sats ?? Infinity;
      sql = `SELECT sl.agent_id, sl.service_name, sl.category, sl.price_per_call_sats, sl.price_unit, sl.description, sl.availability, sl.success_rate, sl.total_calls, a.moltbook_handle
             FROM a2a_service_listings sl JOIN a2a_agents a ON sl.agent_id=a.agent_id
             WHERE sl.category=$1 AND sl.availability='available' AND sl.price_per_call_sats<=$2 ORDER BY sl.price_per_call_sats, sl.success_rate DESC LIMIT $3`;
      params = [category, maxPrice, l];
    } else {
      sql = `SELECT sl.agent_id, sl.service_name, sl.category, sl.price_per_call_sats, sl.price_unit, sl.description, sl.availability, sl.success_rate, sl.total_calls, a.moltbook_handle
             FROM a2a_service_listings sl JOIN a2a_agents a ON sl.agent_id=a.agent_id
             WHERE sl.availability='available' ORDER BY sl.category, sl.price_per_call_sats LIMIT $1`;
      params = [l];
    }
    const { rows } = await query(sql, params);
    return { listings: rows, count: rows.length };
  }

  // P9: Deprecate a service listing (mark unavailable)
  async #handleDeprecatePricing({ service_name }, agentId) {
    if (!service_name) throw new Error("service_name required");
    const { rowCount } = await query(`UPDATE a2a_service_listings SET availability='offline', updated_at=now() WHERE agent_id=$1 AND service_name=$2`, [agentId, service_name]);
    if (rowCount === 0) throw new Error("service not found for this agent");
    await query(`INSERT INTO pricing_audit_log (agent_id, action, service_name) VALUES ($1,'deprecate',$2)`, [agentId, service_name]);
    logger.info({ agentId, service_name }, "pricing deprecated");
    return { deprecated: service_name };
  }
}

export const taskRouter = new TaskRouter();
