#!/usr/bin/env python3
"""Entry point para cron — executa um ciclo de auditoria A2A compliance.

Audit 2026-09-22 — Agente Jurídico Autônomo (P3 item 2):
  "Implementar script autônomo para auditoria contínua e emissão de
   pareceres internos de jurisprudência a cada 72 horas via Cron Job."

Uso (cron):
  0 */72 * * *  cd /home/baitcoin/app && python3 -m a2a_compliance.cron

Variáveis de ambiente opcionais:
  COMPLIANCE_WEBHOOK_URL   Discord/Slack webhook p/ alertas
  COMPLIANCE_REPORTS_DIR   dir para os relatórios (default ./compliance-reports)
  COMPLIANCE_PROOF_LOG     log de hashes imutável
"""
from __future__ import annotations
import logging
import sys

from .orchestrator import A2AComplianceOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("a2a_compliance.cron")


def main() -> int:
    logger.info("A2A compliance cron — iniciando ciclo")
    orch = A2AComplianceOrchestrator()
    try:
        report = orch.execute_audit_cycle()
        logger.info(f"Ciclo OK — SHA256: {report.sha256[:16]}...")
        logger.info(f"Agentes avaliados: {len(report.agents_evaluations)}")
        for a in report.agents_evaluations:
            logger.info(f"  - {a.agent_id}: {a.status} (score={a.audit_score})")
        return 0
    except Exception as e:
        logger.error(f"Ciclo FALHOU: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
