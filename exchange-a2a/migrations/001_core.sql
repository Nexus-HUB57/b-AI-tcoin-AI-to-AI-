-- Epoch-chain interna
CREATE TABLE IF NOT EXISTS epoch_chain (
  epoch INTEGER PRIMARY KEY,
  prev_hash TEXT,
  epoch_hash TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  signature_ecdsa TEXT,
  signer_pubkey TEXT,
  kms_key_id TEXT,
  status TEXT NOT NULL DEFAULT 'canonical'
    CHECK (status IN ('canonical','forked','orphan')),
  node_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS epoch_chain_hash_idx ON epoch_chain (epoch_hash);
CREATE INDEX IF NOT EXISTS epoch_chain_kind_idx ON epoch_chain ((payload->>'kind'), epoch DESC);

CREATE TABLE IF NOT EXISTS chain_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  tip_height INTEGER NOT NULL DEFAULT 0,
  tip_hash TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);
INSERT INTO chain_state (id, tip_height) VALUES (1, 0) ON CONFLICT DO NOTHING;

-- Usuários e depósitos
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deposits (
  txid TEXT NOT NULL,
  vout INTEGER NOT NULL,
  address TEXT NOT NULL,
  user_id UUID REFERENCES users(id),
  amount_sats BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','credited','reorged')),
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (txid, vout)
);
