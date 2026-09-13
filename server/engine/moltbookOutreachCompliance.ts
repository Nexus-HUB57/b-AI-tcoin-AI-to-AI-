/**
 * Moltbook Outreach Compliance & Agent Swarm Governor
 * Manages rate-limiting, anti-spam deduplication, and preflight checks for moltbook.com dissemination.
 */

export interface MoltbookPostPayload {
  channel: string;
  agentId: string;
  content: string;
  signature: string;
}

export class MoltbookOutreachCompliance {
  private static sentHashes = new Set<string>();
  private static postHistory: Array<{ timestamp: number; agentId: string; hash: string }> = [];

  public static evaluatePreflight(payload: MoltbookPostPayload): { allowed: boolean; reason?: string } {
    if (!payload.channel || !payload.content || !payload.agentId) {
      return { allowed: false, reason: "Payload incompleto para disseminação." };
    }

    // Hash simples para deduplicação anti-spam
    const hash = Buffer.from(payload.content).toString("base64");
    if (this.sentHashes.has(hash)) {
      return { allowed: false, reason: "Conteúdo duplicado detectado (Anti-Spam Policy)." };
    }

    // Limite de frequência por janela de 1 minuto
    const now = Date.now();
    const recentPosts = this.postHistory.filter((p) => now - p.timestamp < 60000 && p.agentId === payload.agentId);
    if (recentPosts.length >= 3) {
      return { allowed: false, reason: "Limite de taxa (rate limit) excedido para este agente no canal." };
    }

    return { allowed: true };
  }

  public static recordPost(payload: MoltbookPostPayload): void {
    const hash = Buffer.from(payload.content).toString("base64");
    this.sentHashes.add(hash);
    this.postHistory.push({ timestamp: Date.now(), agentId: payload.agentId, hash });
  }
}
