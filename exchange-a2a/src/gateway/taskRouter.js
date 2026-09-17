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
}

export const taskRouter = new TaskRouter();
