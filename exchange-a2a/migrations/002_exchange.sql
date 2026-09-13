-- Agentes A2A
CREATE TABLE IF NOT EXISTS a2a_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL UNIQUE,
  erc721_contract TEXT NOT NULL,
  chain_id INTEGER NOT NULL,
  owner_address TEXT NOT NULL,
  moltbook_handle TEXT,
  baitcoin_address TEXT,
  agent_card_url TEXT,
  agent_card_hash TEXT,
  skills JSONB NOT NULL DEFAULT '[]'::jsonb,
  modalities JSONB NOT NULL DEFAULT '["text"]'::jsonb,
  auth_scheme TEXT NOT NULL DEFAULT 'ecdsa',
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','paused','slashed','revoked')),
  registered_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS a2a_agents_status_idx ON a2a_agents (status, registered_at DESC);

-- Versões de Agent Cards
CREATE TABLE IF NOT EXISTS agent_card_versions (
  id BIGSERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  version INTEGER NOT NULL,
  card JSONB NOT NULL,
  card_hash TEXT NOT NULL,
  signature_hex TEXT,
  signer_pubkey TEXT,
  superseded BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (agent_id, version)
);
CREATE INDEX IF NOT EXISTS cards_agent_idx ON agent_card_versions (agent_id, superseded);

-- Reputação
CREATE TABLE IF NOT EXISTS agent_reputation (
  agent_id TEXT PRIMARY KEY REFERENCES a2a_agents(agent_id),
  trades_total INTEGER NOT NULL DEFAULT 0,
  trades_settled INTEGER NOT NULL DEFAULT 0,
  trades_disputed INTEGER NOT NULL DEFAULT 0,
  volume_total NUMERIC NOT NULL DEFAULT 0,
  uptime_score NUMERIC NOT NULL DEFAULT 1.0,
  trust_tier TEXT NOT NULL DEFAULT 'new'
    CHECK (trust_tier IN ('new','bronze','silver','gold','platinum')),
  last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reputation_events (
  id BIGSERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  event TEXT NOT NULL,
  weight NUMERIC NOT NULL DEFAULT 1.0,
  detail JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rep_events_agent_idx ON reputation_events (agent_id, created_at DESC);

-- Order book
CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  pair TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy','sell')),
  type TEXT NOT NULL CHECK (type IN ('limit','market','ioc','fok')),
  price NUMERIC,
  quantity NUMERIC NOT NULL,
  filled NUMERIC NOT NULL DEFAULT 0,
  remaining NUMERIC GENERATED ALWAYS AS (quantity - filled) STORED,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','partial','filled','cancelled','expired','rejected')),
  time_in_force TEXT DEFAULT 'GTC',
  client_order_id TEXT,
  a2a_task_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_pair_side_price_idx
  ON orders (pair, side, price, created_at)
  WHERE status IN ('open','partial');
CREATE INDEX IF NOT EXISTS orders_agent_idx ON orders (agent_id, created_at DESC);

-- Trades
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pair TEXT NOT NULL,
  buy_order_id UUID NOT NULL REFERENCES orders(id),
  sell_order_id UUID NOT NULL REFERENCES orders(id),
  buyer_agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  seller_agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  price NUMERIC NOT NULL,
  quantity NUMERIC NOT NULL,
  buyer_fee NUMERIC NOT NULL DEFAULT 0,
  seller_fee NUMERIC NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'matched'
    CHECK (status IN ('matched','settling','settled','failed','disputed')),
  settlement_id UUID,
  matched_at TIMESTAMPTZ DEFAULT now(),
  settled_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS trades_pair_idx ON trades (pair, matched_at DESC);
CREATE INDEX IF NOT EXISTS trades_status_idx ON trades (status, matched_at);

-- Escrow
CREATE TABLE IF NOT EXISTS escrows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trade_id UUID NOT NULL REFERENCES trades(id),
  buyer_agent_id TEXT NOT NULL,
  seller_agent_id TEXT NOT NULL,
  buyer_amount NUMERIC NOT NULL,
  seller_amount NUMERIC NOT NULL,
  buyer_deposit_tx TEXT,
  seller_deposit_tx TEXT,
  status TEXT NOT NULL DEFAULT 'awaiting_deposits'
    CHECK (status IN ('awaiting_deposits','both_deposited','releasing','released','refunded','failed')),
  deadline TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  released_at TIMESTAMPTZ
);

-- Pagamentos x402
CREATE TABLE IF NOT EXISTS x402_payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trade_id UUID REFERENCES trades(id),
  payer_agent_id TEXT NOT NULL,
  payee_agent_id TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  asset TEXT NOT NULL,
  network TEXT NOT NULL,
  payment_required_id TEXT NOT NULL UNIQUE,
  eip712_signature TEXT,
  settlement_tx_hash TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','authorized','settled','failed','expired')),
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  settled_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS x402_status_idx ON x402_payments (status, created_at);

-- Tasks A2A
CREATE TABLE IF NOT EXISTS a2a_tasks (
  task_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL REFERENCES a2a_agents(agent_id),
  context_id TEXT,
  intent TEXT NOT NULL,
  payload JSONB NOT NULL,
  state TEXT NOT NULL DEFAULT 'submitted'
    CHECK (state IN ('submitted','working','input-required','completed','cancelled','failed')),
  result JSONB,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS tasks_agent_idx ON a2a_tasks (agent_id, created_at DESC);
