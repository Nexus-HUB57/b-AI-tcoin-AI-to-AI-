import { router, publicProcedure } from "../_core/trpc";
import { MainnetExecutionEngine } from "../mainnet/mainnetExecutionEngine";
import { PhdHarnessAgentEngine } from "../engine/phdHarnessAgentEngine";
import { MasterWalletGuard } from "../wallet/masterWalletGuard";
import { T1TrillionValuationProtocol } from "../protocol/t1TrillionValuationProtocol";
import { RustConsensusTelemetry } from "../consensus/rustConsensusTelemetry";
import { RustBlockExplorer } from "../consensus/rustBlockExplorer";

export const agentSwarmRouter = router({
  getSwarmStatus: publicProcedure.query(() => {
    const mainnetStatus = MainnetExecutionEngine.getSystemStatus();
    const phdEngine = PhdHarnessAgentEngine.getEngineMetrics();
    const walletState = MasterWalletGuard.getMasterWalletState();
    const valuationRoadmap = T1TrillionValuationProtocol.getValuationRoadmap();

    return {
      status: "ACTIVE",
      network: mainnetStatus.network,
      nodes: mainnetStatus.nodes,
      activePrimaryNode: mainnetStatus.activePrimaryNode,
      phdAgents: phdEngine.agents,
      masterWallet: walletState.masterAddress,
      valuationMilestones: valuationRoadmap,
      timestamp: Date.now()
    };
  }),

  getRustConsensusMetrics: publicProcedure.query(() => {
    return RustConsensusTelemetry.getMetrics();
  }),

  getInspectableBlocks: publicProcedure.query(() => {
    return RustBlockExplorer.getInspectableBlocks();
  })
});
