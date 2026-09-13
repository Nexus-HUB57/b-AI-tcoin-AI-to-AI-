/**
 * Master Workers tRPC Router
 * Exposes real-time telemetry and metrics for the 20 high-performance native compute nodes.
 */

import { router, protectedProcedure } from "../_core/trpc";
import { MasterWorkerOrchestrator } from "../engine/masterWorkerOrchestrator";

export const masterWorkersRouter = router({
  getSummary: protectedProcedure.query(() => {
    return MasterWorkerOrchestrator.getOrchestratorSummary();
  }),
  listWorkers: protectedProcedure.query(() => {
    return MasterWorkerOrchestrator.activate20Workers();
  }),
  getHistory: protectedProcedure.query(() => {
    return WorkerExecutionHistory.getHistory();
  }),
});
import { WorkerExecutionHistory } from "../engine/workerExecutionHistory";
