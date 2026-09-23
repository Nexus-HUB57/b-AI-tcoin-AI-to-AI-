-- ================================================================
-- Migration 003: A2A Pricing Tables
-- P9: Each agent publishes a pricing table in BAIT for A2A services
-- ================================================================

-- Add pricing JSONB column to a2a_agents
-- Schema: { "services": [{ "name": str, "category": str, "price_per_call_sats": int, "unit": str, "description": str }] }
ALTER TABLE a2a_agents ADD COLUMN IF NOT EXISTS pricing JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Add pricing_updated_at timestamp
ALTER TABLE a2a_agents ADD COLUMN IF NOT EXISTS pricing_updated_at TIMESTAMPTZ;

-- Index for querying agents by service category and price
CREATE INDEX IF NOT EXISTS a2a_agents_pricing_idx ON a2a_agents USING GIN (pricing jsonb_path_ops);

-- Create a2a_service_listings table for published services
CREATE TABLE IF NOT EXISTS a2a_service_listings (
  id BIGSERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  service_name TEXT NOT NULL,
  category TEXT NOT NULL,
  price_per_call_sats INTEGER NOT NULL CHECK (price_per_call_sats >= 0),
  price_unit TEXT NOT NULL DEFAULT 'BAIT',
  description TEXT,
  min_commitment_sats INTEGER DEFAULT 0,
  max_commitment_sats INTEGER,
  availability TEXT NOT NULL DEFAULT 'available'
    CHECK (availability IN ('available','busy','offline')),
  avg_response_ms INTEGER,
  success_rate NUMERIC DEFAULT 1.0,
  total_calls INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (agent_id, service_name)
);

CREATE INDEX IF NOT EXISTS service_listings_category_idx ON a2a_service_listings (category, availability, price_per_call_sats);
CREATE INDEX IF NOT EXISTS service_listings_agent_idx ON a2a_service_listings (agent_id, availability);

-- Create audit trail for pricing changes
CREATE TABLE IF NOT EXISTS pricing_audit_log (
  id BIGSERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  action TEXT NOT NULL CHECK (action IN ('publish','update','deprecate','remove')),
  service_name TEXT NOT NULL,
  old_price_sats INTEGER,
  new_price_sats INTEGER,
  detail JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS pricing_audit_agent_idx ON pricing_audit_log (agent_id, created_at DESC);
