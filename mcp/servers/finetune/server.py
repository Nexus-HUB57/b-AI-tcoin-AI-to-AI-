r"""
mcp-finetune — LoRA/QLoRA fine-tuning pipeline with tracking.

Tools:
  create_job(base_model, dataset_path, lora_rank, lora_alpha)
  job_status(job_id)
  list_jobs()
  cancel_job(job_id)
  export_adapter(job_id, output_path)
  recommend_hyperparams(base_model, dataset_size)
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


JOBS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-finetune", version="1.0.0", title="Fine-Tuning Pipeline", description="LoRA/QLoRA fine-tuning job management with hyperparameter recommendation.")


@server.tool(description="Create a fine-tuning job")
def create_job(base_model: str, dataset_path: str, lora_rank: int = 16, lora_alpha: int = 32) -> dict:
    job_id = _hash("job", base_model, dataset_path, time.time())
    JOBS[job_id] = {
        "job_id": job_id,
        "base_model": base_model,
        "dataset_path": dataset_path,
        "lora_rank": lora_rank,
        "lora_alpha": lora_alpha,
        "state": "queued",
        "created_at": time.time(),
        "metrics": {"loss": None, "accuracy": None, "epoch": 0},
    }
    return {"ok": True, "job_id": job_id, "state": "queued"}


@server.tool(description="Status of a fine-tuning job")
def job_status(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    return j


@server.tool(description="List all jobs")
def list_jobs() -> dict:
    return {"jobs": list(JOBS.values()), "count": len(JOBS)}


@server.tool(description="Cancel a queued/running job")
def cancel_job(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    if j["state"] in ("completed", "cancelled"):
        return {"ok": False, "error": f"cannot_cancel_state_{j['state']}"}
    j["state"] = "cancelled"
    return {"ok": True, "job_id": job_id, "state": "cancelled"}


@server.tool(description="Export the LoRA adapter artifact")
def export_adapter(job_id: str, output_path: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    if j["state"] != "completed":
        return {"ok": False, "error": f"job_not_completed_state_{j['state']}"}
    return {"ok": True, "job_id": job_id, "output_path": output_path, "sha256": _hash(job_id, output_path)}


@server.tool(description="Recommend LoRA hyperparameters given base model and dataset size")
def recommend_hyperparams(base_model: str, dataset_size: int = 1000) -> dict:
    if dataset_size < 100:
        rank, alpha, lr = 4, 8, 2e-4
    elif dataset_size < 1000:
        rank, alpha, lr = 8, 16, 1e-4
    elif dataset_size < 10000:
        rank, alpha, lr = 16, 32, 5e-5
    else:
        rank, alpha, lr = 32, 64, 2e-5
    return {"base_model": base_model, "dataset_size": dataset_size, "lora_rank": rank, "lora_alpha": alpha, "learning_rate": lr, "epochs": 3}


if __name__ == "__main__":
    server.run()