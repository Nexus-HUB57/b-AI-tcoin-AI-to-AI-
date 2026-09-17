r"""
mcp-scheduler — Cron-like scheduler for agent tasks with retries.

Tools:
  schedule(name, cron, payload, max_retries)
  list_jobs()
  get_job(job_id)
  cancel_job(job_id)
  run_now(job_id)
  job_history(job_id, limit)
  next_run(cron_expression)
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


def _parse_cron(expr: str) -> int:
    """Naive: assume a single number in seconds."""
    if expr.isdigit():
        return int(expr)
    if expr.endswith("s"):
        return int(expr[:-1])
    if expr.endswith("m"):
        return int(expr[:-1]) * 60
    if expr.endswith("h"):
        return int(expr[:-1]) * 3600
    return 3600


server = Server(name="mcp-scheduler", version="1.0.0", title="Task Scheduler", description="Cron-style scheduler for agent tasks with retry policies.")


@server.tool(description="Schedule a recurring job")
def schedule(name: str, cron: str, payload: dict, max_retries: int = 3) -> dict:
    jid = _hash("job", name, cron, time.time())
    interval = _parse_cron(cron)
    JOBS[jid] = {
        "job_id": jid,
        "name": name,
        "cron": cron,
        "interval_s": interval,
        "payload": payload,
        "max_retries": max_retries,
        "state": "scheduled",
        "next_run_at": time.time() + interval,
        "created_at": time.time(),
        "history": [],
    }
    return {"ok": True, "job_id": jid, "next_run_at": JOBS[jid]["next_run_at"]}


@server.tool(description="List all scheduled jobs")
def list_jobs() -> dict:
    return {"jobs": [{"job_id": j["job_id"], "name": j["name"], "state": j["state"], "next_run_at": j["next_run_at"]} for j in JOBS.values()]}


@server.tool(description="Get a single job")
def get_job(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    return j


@server.tool(description="Cancel a scheduled job")
def cancel_job(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    j["state"] = "cancelled"
    return {"ok": True, "job_id": job_id}


@server.tool(description="Trigger an immediate run")
def run_now(job_id: str) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    run_id = _hash("run", job_id, time.time())
    j["history"].append({"run_id": run_id, "ts": time.time(), "status": "started"})
    return {"ok": True, "run_id": run_id, "job_id": job_id}


@server.tool(description="Get the run history of a job")
def job_history(job_id: str, limit: int = 50) -> dict:
    j = JOBS.get(job_id)
    if not j:
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "history": j["history"][-limit:]}


@server.tool(description="Compute the next run time for a cron expression (seconds-from-now)")
def next_run(cron_expression: str) -> dict:
    interval = _parse_cron(cron_expression)
    return {"ok": True, "expression": cron_expression, "interval_s": interval, "next_run_at": time.time() + interval}


if __name__ == "__main__":
    server.run()