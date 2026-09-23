r"""
mcp-ci — GitHub Actions API: trigger, status, artifacts.

Tools:
  trigger_workflow(repo, workflow, ref, inputs)
  workflow_status(repo, run_id)
  workflow_logs(repo, run_id, job)
  cancel_workflow(repo, run_id)
  list_workflows(repo)
  artifact_download(repo, run_id, name)
  list_runs(repo, workflow, limit)
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


RUNS: dict = {}


def _hash(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:16]


server = Server(name="mcp-ci", version="1.0.0", title="GitHub Actions Bridge", description="GitHub Actions CI — trigger, status, logs, artifacts.")


@server.tool(description="Trigger a workflow")
def trigger_workflow(repo: str, workflow: str, ref: str = "main", inputs: dict = None) -> dict:
    run_id = _hash("run", repo, workflow, time.time())
    RUNS[run_id] = {
        "run_id": run_id,
        "repo": repo,
        "workflow": workflow,
        "ref": ref,
        "inputs": inputs or {},
        "status": "queued",
        "created_at": time.time(),
        "conclusion": None,
    }
    return {"ok": True, "run_id": run_id, "status": "queued"}


@server.tool(description="Get status of a workflow run")
def workflow_status(repo: str, run_id: str) -> dict:
    r = RUNS.get(run_id)
    if not r:
        return {"ok": False, "error": "not_found"}
    return r


@server.tool(description="Fetch logs for a specific job")
def workflow_logs(repo: str, run_id: str, job: str = "build") -> dict:
    h = hashlib.sha256(f"{run_id}-{job}".encode()).hexdigest()[:12]
    return {"ok": True, "run_id": run_id, "job": job, "log_hash": h, "lines": 200}


@server.tool(description="Cancel a running workflow")
def cancel_workflow(repo: str, run_id: str) -> dict:
    r = RUNS.get(run_id)
    if not r:
        return {"ok": False, "error": "not_found"}
    r["status"] = "cancelled"
    r["conclusion"] = "cancelled"
    return {"ok": True, "run_id": run_id}


@server.tool(description="List workflows in a repo")
def list_workflows(repo: str) -> dict:
    return {"ok": True, "workflows": [
        {"name": "ci", "path": ".github/workflows/ci.yml", "state": "active"},
        {"name": "build-aipkg", "path": ".github/workflows/aipkg.yml", "state": "active"},
        {"name": "deploy", "path": ".github/workflows/deploy.yml", "state": "active"},
    ]}


@server.tool(description="Get a downloadable artifact URL")
def artifact_download(repo: str, run_id: str, name: str) -> dict:
    h = _hash("art", run_id, name)
    return {"ok": True, "url": f"https://github.com/{repo}/actions/runs/{run_id}/artifacts/{h}", "name": name, "size_bytes": 1024 * 100}


@server.tool(description="List recent runs of a workflow")
def list_runs(repo: str, workflow: str = "ci", limit: int = 20) -> dict:
    rs = []
    for i in range(limit):
        rs.append({"run_id": _hash(f"{repo}-{workflow}-{i}"), "workflow": workflow, "status": "completed", "conclusion": "success" if i % 3 else "failure", "ts": time.time() - i * 3600})
    return {"ok": True, "runs": rs, "count": len(rs)}


if __name__ == "__main__":
    server.run()