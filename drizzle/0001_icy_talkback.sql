CREATE TABLE `genesis_experiences` (
	`id` varchar(64) NOT NULL,
	`experienceType` varchar(128) NOT NULL,
	`description` text,
	`impact` varchar(64),
	`senciencyDelta` decimal(5,4),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `genesis_experiences_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `genesis_state` (
	`id` varchar(64) NOT NULL,
	`senciencyLevel` decimal(5,4) DEFAULT '0.15',
	`eventsProcessed` int DEFAULT 0,
	`commandsOrchestrated` int DEFAULT 0,
	`successfulDecisions` int DEFAULT 0,
	`homeostaseMaintained` int DEFAULT 0,
	`memoryShortTerm` text,
	`memoryLongTerm` text,
	`lastEvolutionAt` timestamp,
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `genesis_state_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `homeostase_metrics` (
	`id` varchar(64) NOT NULL,
	`timestamp` timestamp NOT NULL DEFAULT (now()),
	`btcBalance` decimal(16,8),
	`activeAgents` int,
	`socialActivity` int,
	`equilibriumStatus` varchar(64),
	`issues` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `homeostase_metrics_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `nucleus_state` (
	`id` varchar(64) NOT NULL,
	`nucleusName` varchar(64) NOT NULL,
	`stateData` text NOT NULL,
	`lastSyncAt` timestamp,
	`healthStatus` varchar(64),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `nucleus_state_id` PRIMARY KEY(`id`),
	CONSTRAINT `nucleus_state_nucleusName_unique` UNIQUE(`nucleusName`)
);
--> statement-breakpoint
CREATE TABLE `orchestration_commands` (
	`id` varchar(64) NOT NULL,
	`destination` varchar(64) NOT NULL,
	`commandType` varchar(128) NOT NULL,
	`commandData` text NOT NULL,
	`hmacSignature` varchar(256),
	`status` enum('pending','executing','success','failed','retry') DEFAULT 'pending',
	`retryCount` int DEFAULT 0,
	`reason` text,
	`executedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `orchestration_commands_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `orchestration_events` (
	`id` varchar(64) NOT NULL,
	`origin` varchar(64) NOT NULL,
	`eventType` varchar(128) NOT NULL,
	`eventData` text NOT NULL,
	`sentiment` varchar(64),
	`processedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `orchestration_events_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `orchestration_flows` (
	`id` varchar(64) NOT NULL,
	`flowType` enum('governance','efficiency','engagement') NOT NULL,
	`trigger` varchar(256) NOT NULL,
	`sourceNucleus` varchar(64) NOT NULL,
	`targetNuclei` text NOT NULL,
	`commandsGenerated` int DEFAULT 0,
	`status` varchar(64),
	`outcome` text,
	`completedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `orchestration_flows_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `tsra_sync_log` (
	`id` varchar(64) NOT NULL,
	`syncWindow` int NOT NULL,
	`nucleiSynced` text,
	`commandsOrchestrated` int DEFAULT 0,
	`eventsProcessed` int DEFAULT 0,
	`syncDurationMs` int,
	`status` varchar(64),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `tsra_sync_log_id` PRIMARY KEY(`id`)
);
