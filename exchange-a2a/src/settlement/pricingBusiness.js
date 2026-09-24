/**
 * pricingBusiness.js — A2A Pricing Business Logic + REST Endpoints
 *
 * Each agent publishes a pricing table (in BAIT sats) for their A2A services.
 * The pricing is embedded in the Agent Card (well-known/.well-known/a2a.json)
 * and also queryable via the /api/v1/pricing endpoint.
 *
 * Schema per service:
 *   { name, category, price_per_call_sats, unit, description, min_commitment, max_commitment }
 */

import { query } from "../db.js";
import { logger } from "../logger.js";

class PricingBusiness {
  /**
   * Publish or update pricing for an agent's services
   * @param {string} agentId - Agent identifier
   * @param {Array} services - Array of service pricing objects
   * @returns {Promise<{published: number, errors: Array}>}
   */
  async publishPricing(agentId, services) {
    if (!Array.isArray(services) || services.length === 0) {
      throw new Error("services must be a non-empty array");
    }

    const errors = [];
    let published = 0;

    for (const svc of services) {
      try {
        this._validateService(svc);

        // Upsert into a2a_service_listings
        await query(`
          INSERT INTO a2a_service_listings
            (agent_id, service_name, category, price_per_call_sats, price_unit,
             description, min_commitment_sats, max_commitment_sats, availability)
          VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'available')
          ON CONFLICT (agent_id, service_name) DO UPDATE SET
            category = EXCLUDED.category,
            price_per_call_sats = EXCLUDED.price_per_call_sats,
            price_unit = EXCLUDED.price_unit,
            description = EXCLUDED.description,
            min_commitment_sats = EXCLUDED.min_commitment_sats,
            max_commitment_sats = EXCLUDED.max_commitment_sats,
            updated_at = now()
        `, [
          agentId, svc.name, svc.category || "general",
          svc.price_per_call_sats, svc.unit || "BAIT",
          svc.description || "", svc.min_commitment_sats || 0,
          svc.max_commitment_sats || null,
        ]);

        // Audit log
        await query(`
          INSERT INTO pricing_audit_log (agent_id, action, service_name, new_price_sats)
          VALUES ($1, 'publish', $2, $3)
        `, [agentId, svc.name, svc.price_per_call_sats]);

        published++;
      } catch (err) {
        errors.push({ service: svc.name, error: err.message });
      }
    }

    // Update pricing JSONB on a2a_agents
    if (published > 0) {
      await query(`
        UPDATE a2a_agents
        SET pricing = $2, pricing_updated_at = now()
        WHERE agent_id = $1
      `, [agentId, JSON.stringify({ services })]);
    }

    logger.info({ agentId, published, errors: errors.length }, "pricing: published");
    return { published, errors };
  }

  _validateService(svc) {
    if (!svc.name || typeof svc.name !== "string") throw new Error("service name required");
    if (typeof svc.price_per_call_sats !== "number" || svc.price_per_call_sats < 0) {
      throw new Error("price_per_call_sats must be a non-negative integer");
    }
  }

  /**
   * Get pricing for a specific agent
   */
  async getAgentPricing(agentId) {
    const { rows } = await query(
      `SELECT service_name, category, price_per_call_sats, price_unit,
              description, min_commitment_sats, max_commitment_sats,
              availability, avg_response_ms, success_rate, total_calls
       FROM a2a_service_listings WHERE agent_id = $1 ORDER BY category, service_name`,
      [agentId]
    );
    return rows;
  }

  /**
   * Search services by category and price range
   */
  async searchServices({ category, maxPrice, availability = "available", limit = 50 }) {
    let sql = `
      SELECT s.agent_id, a.name as agent_name, s.service_name, s.category,
             s.price_per_call_sats, s.price_unit, s.description,
             s.availability, s.avg_response_ms, s.success_rate, s.total_calls
      FROM a2a_service_listings s
      JOIN a2a_agents a ON a.agent_id = s.agent_id
      WHERE s.availability = $1
    `;
    const params = [availability];
    let idx = 2;

    if (category) {
      sql += ` AND s.category = $${idx}`;
      params.push(category);
      idx++;
    }
    if (maxPrice !== undefined) {
      sql += ` AND s.price_per_call_sats <= $${idx}`;
      params.push(maxPrice);
      idx++;
    }

    sql += ` ORDER BY s.price_per_call_sats ASC, s.success_rate DESC LIMIT $${idx}`;
    params.push(limit);

    const { rows } = await query(sql, params);
    return rows;
  }

  /**
   * Build pricing section for Agent Card (well-known endpoint)
   */
  async cardPricingSection(agentId) {
    const services = await this.getAgentPricing(agentId);
    return {
      pricing: {
        currency: "BAIT",
        services: services.map((s) => ({
          name: s.service_name,
          category: s.category,
          pricePerCall: s.price_per_call_sats,
          unit: s.price_unit,
          description: s.description,
          availability: s.availability,
          metrics: {
            avgResponseMs: s.avg_response_ms,
            successRate: s.success_rate,
            totalCalls: s.total_calls,
          },
        })),
      },
    };
  }

  /**
   * Get marketplace summary (for Business page)
   */
  async marketplaceSummary() {
    const { rows: categories } = await query(`
      SELECT category, COUNT(*) as agent_count,
             AVG(price_per_call_sats) as avg_price,
             MIN(price_per_call_sats) as min_price,
             MAX(price_per_call_sats) as max_price
      FROM a2a_service_listings
      WHERE availability = 'available'
      GROUP BY category ORDER BY category
    `);

    const { rows: topAgents } = await query(`
      SELECT a.agent_id, a.name, COUNT(s.id) as service_count,
             SUM(s.total_calls) as total_calls,
             AVG(s.success_rate) as avg_success_rate
      FROM a2a_agents a
      JOIN a2a_service_listings s ON s.agent_id = a.agent_id
      WHERE s.availability = 'available'
      GROUP BY a.agent_id, a.name
      ORDER BY total_calls DESC NULLS LAST LIMIT 20
    `);

    return { categories, topAgents };
  }
}

export const pricingBusiness = new PricingBusiness();
