"""Schemas Pydantic para padronizar outputs dos agentes A2A de compliance.

Audit 2026-09-22 — PhD Compliance (P3 item 1):
  "Padronização de Schema JSON & Hash SHA-256: Garantia de que as saídas
   dos agentes (Dr. DDK e Dra. PWC) sigam uma estrutura estrita e gerem
   hashes imutáveis para auditoria."
"""
from __future__ import annotations
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentAuditReport(BaseModel):
    """Schema canônico para saída de agente A2A de compliance."""
    model_config = ConfigDict(extra="forbid", frozen=False)

    agent_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$",
                          description="Identificador único do agente AI")
    timestamp: int = Field(..., ge=0, description="Unix timestamp da execução")
    environment: str = Field(default="E2E-Compliance", max_length=64)
    status: Literal["APPROVED", "REJECTED", "WARNING", "ERROR"] = Field(
        ..., description="Status de conformidade")
    audit_score: float = Field(..., ge=0.0, le=100.0,
                               description="Score entre 0 e 100")
    findings: List[str] = Field(default_factory=list, max_length=100)
    legal_disclaimer: str = Field(
        default="Esta análise é técnica heurística INTERNA e NÃO substitui parecer "
                "formal de escritório de advocacia habilitado. Não constitui opinião legal.",
        description="Aviso legal obrigatório")
    evidence_refs: List[str] = Field(default_factory=list, max_length=50,
                                     description="Refs p/ SHA-256 hashes de artefatos")
    tags: List[str] = Field(default_factory=list, max_length=20)


class ConsolidatedComplianceReport(BaseModel):
    """Schema do relatório consolidado do ciclo de auditoria."""
    model_config = ConfigDict(extra="forbid")

    execution_time: str = Field(..., description="ISO 8601")
    environment: str = Field(default="E2E-Compliance")
    agents_evaluations: List[AgentAuditReport] = Field(..., min_length=1)
    sha256: str = Field(..., min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$",
                        description="SHA-256 do payload serializado")
    schema_version: str = Field(default="1.0.0")


class HealthStatus(BaseModel):
    """Schema p/ health check do orchestrator."""
    model_config = ConfigDict(extra="forbid")

    status: Literal["healthy", "degraded", "unhealthy"]
    last_cycle_ts: Optional[int] = None
    last_cycle_sha256: Optional[str] = None
    cycles_total: int = Field(default=0, ge=0)
    errors_total: int = Field(default=0, ge=0)
