import dotenv from "dotenv";
dotenv.config();

function req(name) {
  const v = process.env[name];
  if (!v) throw new Error(`Env obrigatória ausente: ${name}`);
  return v;
}

export const config = {
  db: { url: req("DATABASE_URL") },
  exchange: {
    port: parseInt(process.env.EXCHANGE_PORT ?? "3001", 10),
    agentId: process.env.EXCHANGE_AGENT_ID ?? "exchange-a2a-main",
  },
  epoch: {
    kmsKeyId: process.env.EPOCH_KMS_KEY_ID || null,
    localPrivkeyHex: process.env.EPOCH_LOCAL_PRIVKEY_HEX || null,
  },
  x402: { mode: process.env.X402_MODE ?? "local" },
  logLevel: process.env.LOG_LEVEL ?? "info",
};
