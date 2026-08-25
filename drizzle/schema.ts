import { decimal, int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Eventos capturados dos núcleos Nexus-in, Nexus-HUB e Fundo Nexus
 */
export const orchestrationEvents = mysqlTable("orchestration_events", {
  id: varchar("id", { length: 64 }).primaryKey(),
  origin: varchar("origin", { length: 64 }).notNull(), // nexus_in, nexus_hub, fundo_nexus
  eventType: varchar("eventType", { length: 128 }).notNull(),
  eventData: text("eventData").notNull(), // JSON
  sentiment: varchar("sentiment", { length: 64 }),
  processedAt: timestamp("processedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type OrchestrationEvent = typeof orchestrationEvents.$inferSelect;
export type InsertOrchestrationEvent = typeof orchestrationEvents.$inferInsert;

/**
 * Comandos orquestrados entre núcleos
 */
export const orchestrationCommands = mysqlTable("orchestration_commands", {
  id: varchar("id", { length: 64 }).primaryKey(),
  destination: varchar("destination", { length: 64 }).notNull(), // nexus_in, nexus_hub, fundo_nexus
  commandType: varchar("commandType", { length: 128 }).notNull(),
  commandData: text("commandData").notNull(), // JSON
  hmacSignature: varchar("hmacSignature", { length: 256 }),
  status: mysqlEnum("status", ["pending", "executing", "success", "failed", "retry"]).default("pending"),
  retryCount: int("retryCount").default(0),
  reason: text("reason"),
  executedAt: timestamp("executedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type OrchestrationCommand = typeof orchestrationCommands.$inferSelect;
export type InsertOrchestrationCommand = typeof orchestrationCommands.$inferInsert;

/**
 * Estado global dos núcleos
 */
export const nucleusState = mysqlTable("nucleus_state", {
  id: varchar("id", { length: 64 }).primaryKey(),
  nucleusName: varchar("nucleusName", { length: 64 }).notNull().unique(),
  stateData: text("stateData").notNull(), // JSON
  lastSyncAt: timestamp("lastSyncAt"),
  healthStatus: varchar("healthStatus", { length: 64 }),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type NucleusState = typeof nucleusState.$inferSelect;
export type InsertNucleusState = typeof nucleusState.$inferInsert;

/**
 * Métricas de homeostase do ecossistema
 */
export const homeostaseMetrics = mysqlTable("homeostase_metrics", {
  id: varchar("id", { length: 64 }).primaryKey(),
  timestamp: timestamp("timestamp").defaultNow().notNull(),
  btcBalance: decimal("btcBalance", { precision: 16, scale: 8 }),
  activeAgents: int("activeAgents"),
  socialActivity: int("socialActivity"),
  equilibriumStatus: varchar("equilibriumStatus", { length: 64 }),
  issues: text("issues"), // JSON array
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type HomeostaseMetric = typeof homeostaseMetrics.$inferSelect;
export type InsertHomeostaseMetric = typeof homeostaseMetrics.$inferInsert;

/**
 * Experiências e aprendizados do Nexus Genesis
 */
export const genesisExperiences = mysqlTable("genesis_experiences", {
  id: varchar("id", { length: 64 }).primaryKey(),
  experienceType: varchar("experienceType", { length: 128 }).notNull(),
  description: text("description"),
  impact: varchar("impact", { length: 64 }),
  senciencyDelta: decimal("senciencyDelta", { precision: 5, scale: 4 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type GenesisExperience = typeof genesisExperiences.$inferSelect;
export type InsertGenesisExperience = typeof genesisExperiences.$inferInsert;

/**
 * Logs de sincronização TSRA
 */
export const tsraSyncLog = mysqlTable("tsra_sync_log", {
  id: varchar("id", { length: 64 }).primaryKey(),
  syncWindow: int("syncWindow").notNull(),
  nucleiSynced: text("nucleiSynced"), // JSON array
  commandsOrchestrated: int("commandsOrchestrated").default(0),
  eventsProcessed: int("eventsProcessed").default(0),
  syncDurationMs: int("syncDurationMs"),
  status: varchar("status", { length: 64 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type TsraSyncLog = typeof tsraSyncLog.$inferSelect;
export type InsertTsraSyncLog = typeof tsraSyncLog.$inferInsert;

/**
 * Estado global de senciência do Genesis
 */
export const genesisState = mysqlTable("genesis_state", {
  id: varchar("id", { length: 64 }).primaryKey(),
  senciencyLevel: decimal("senciencyLevel", { precision: 5, scale: 4 }).default("0.15"),
  eventsProcessed: int("eventsProcessed").default(0),
  commandsOrchestrated: int("commandsOrchestrated").default(0),
  successfulDecisions: int("successfulDecisions").default(0),
  homeostaseMaintained: int("homeostaseMaintained").default(0),
  memoryShortTerm: text("memoryShortTerm"), // JSON - últimos 1000 eventos
  memoryLongTerm: text("memoryLongTerm"), // JSON - experiências significativas
  lastEvolutionAt: timestamp("lastEvolutionAt"),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type GenesisState = typeof genesisState.$inferSelect;
export type InsertGenesisState = typeof genesisState.$inferInsert;

/**
 * Fluxos de orquestração (Governança, Eficiência, Engajamento)
 */
export const orchestrationFlows = mysqlTable("orchestration_flows", {
  id: varchar("id", { length: 64 }).primaryKey(),
  flowType: mysqlEnum("flowType", ["governance", "efficiency", "engagement"]).notNull(),
  trigger: varchar("trigger", { length: 256 }).notNull(),
  sourceNucleus: varchar("sourceNucleus", { length: 64 }).notNull(),
  targetNuclei: text("targetNuclei").notNull(), // JSON array
  commandsGenerated: int("commandsGenerated").default(0),
  status: varchar("status", { length: 64 }),
  outcome: text("outcome"), // JSON
  completedAt: timestamp("completedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type OrchestrationFlow = typeof orchestrationFlows.$inferSelect;
export type InsertOrchestrationFlow = typeof orchestrationFlows.$inferInsert;
