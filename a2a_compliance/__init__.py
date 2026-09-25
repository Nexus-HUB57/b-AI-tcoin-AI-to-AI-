"""a2a_compliance — Orquestração de Agentes AI-to-AI para Compliance.

Audit 2026-09-22 — PhD Compliance (P3-P4):
  Padronização de Schema JSON, validação de invariantes, webhooks de
  emergência, hashing imutável, e aviso legal explícito.

Pacote:
  - schemas.py      — modelos Pydantic (validação rígida)
  - orchestrator.py — orquestrador principal
  - cron.py         — entrypoint p/ cron (executa ciclo de auditoria)

Aviso legal: este módulo é uma análise técnica heurística INTERNA
que NÃO substitui parecer formal de escritório de advocacia
habilitado (OAB/equivalente). Não constitui opinião legal.
"""
__version__ = "1.0.0"
