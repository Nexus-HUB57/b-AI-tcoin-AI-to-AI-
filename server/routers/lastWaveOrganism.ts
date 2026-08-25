import { router, protectedProcedure } from "../_core/trpc";
import { z } from "zod";
import { SkillRegistry } from "../engine/skillRegistry";
import { LangChainRagPipeline } from "../engine/langchainRagPipeline";
import { GenerativeAlgorithmsEngine } from "../engine/generativeAlgorithmsEngine";

export const lastWaveOrganismRouter = router({
  getSkillsCatalog: protectedProcedure.query(() => {
    return SkillRegistry.getCatalog();
  }),
  executeSkill: protectedProcedure
    .input(z.object({ skillId: z.string(), payload: z.any() }))
    .mutation(({ input }) => {
      return SkillRegistry.executeSkill(input.skillId, input.payload);
    }),
  queryRag: protectedProcedure
    .input(z.object({ query: z.string() }))
    .query(({ input }) => {
      return LangChainRagPipeline.query(input.query);
    }),
  getGenerativeStats: protectedProcedure.query(() => {
    return GenerativeAlgorithmsEngine.getCatalogStats();
  }),
  synthesizeAlgorithm: protectedProcedure
    .input(z.object({ prompt: z.string() }))
    .mutation(({ input }) => {
      return GenerativeAlgorithmsEngine.synthesizeAlgorithm(input.prompt);
    }),
});
