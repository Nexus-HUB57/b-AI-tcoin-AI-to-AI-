import { router, protectedProcedure } from "../_core/trpc";
import { AgentAuthorityOrchestrator } from "../engine/agentAuthorityOrchestrator";
import { z } from "zod";

export const agentAuthorityRouter = router({
  getStatus: protectedProcedure.query(() => {
    return AgentAuthorityOrchestrator.getGovernanceStatus();
  }),
  evaluateTask: protectedProcedure
    .input(z.object({
      agentId: z.string(),
      capability: z.enum(["BLOCKCHAIN_MAINNET", "ENTROPIC_OPTIMIZATION", "SWARM_SYNTHESIS"]),
      payload: z.string()
    }))
    .mutation(({ input }) => {
      return AgentAuthorityOrchestrator.evaluateAndDelegate(input.agentId, input.capability, input.payload);
    }),
});
