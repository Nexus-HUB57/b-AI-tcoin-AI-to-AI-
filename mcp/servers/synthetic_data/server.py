r"""
mcp-synthetic-data — Privacy-preserving synthetic data generation.

Tools:
  generate_tabular(schema, n_rows, seed)
  generate_text(template, n_samples, seed)
  generate_timeseries(pattern, n_points, noise, seed)
  privacy_budget(epsilon, delta)
  differential_noise(value, epsilon, sensitivity)
"""

from __future__ import annotations

import hashlib
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from mcp_sdk import Server


server = Server(name="mcp-synthetic-data", version="1.0.0", title="Synthetic Data Generator", description="Privacy-preserving synthetic tabular/text/timeseries generation.")


@server.tool(description="Generate synthetic tabular rows from a JSON schema")
def generate_tabular(schema: dict, n_rows: int = 100, seed: int = 42) -> dict:
    rnd = random.Random(seed)
    cols = []
    rows = []
    for col_name, col_def in schema.items():
        kind = col_def.get("type", "string")
        cols.append({"name": col_name, "type": kind})
    for _ in range(n_rows):
        row = {}
        for c in cols:
            if c["type"] == "int":
                row[c["name"]] = rnd.randint(c.get("min", 0), c.get("max", 1000))
            elif c["type"] == "float":
                row[c["name"]] = round(rnd.uniform(c.get("min", 0.0), c.get("max", 1.0)), 4)
            elif c["type"] == "enum":
                row[c["name"]] = rnd.choice(c["values"])
            elif c["type"] == "email":
                row[c["name"]] = f"user{rnd.randint(1000, 9999)}@example.com"
            else:
                row[c["name"]] = hashlib.sha256(f"{seed}-{c['name']}-{rnd.randint(0, 100000)}".encode()).hexdigest()[:12]
        rows.append(row)
    return {"columns": [c["name"] for c in cols], "rows": rows, "count": len(rows), "seed": seed}


@server.tool(description="Generate synthetic text samples from a template")
def generate_text(template: str, n_samples: int = 10, seed: int = 42) -> dict:
    rnd = random.Random(seed)
    samples = []
    for _ in range(n_samples):
        out = template
        # substitute {name} placeholders with random words
        for m in re.finditer(r"\{(\w+)\}", template):
            key = m.group(1)
            replacement = hashlib.sha256(f"{seed}-{key}-{rnd.randint(0, 100000)}".encode()).hexdigest()[:8]
            out = out.replace("{" + key + "}", replacement)
        samples.append(out)
    return {"samples": samples, "count": len(samples), "seed": seed}


@server.tool(description="Generate synthetic timeseries with a known pattern")
def generate_timeseries(pattern: str = "linear", n_points: int = 100, noise: float = 0.1, seed: int = 42) -> dict:
    rnd = random.Random(seed)
    points = []
    for i in range(n_points):
        t = i / max(1, n_points - 1)
        if pattern == "linear":
            base = t
        elif pattern == "sinusoidal":
            base = 0.5 + 0.5 * math_sin(t * 6.28318)
        elif pattern == "exponential":
            base = t * t
        else:
            base = rnd.random()
        value = base + rnd.uniform(-noise, noise)
        points.append({"t": round(t, 4), "value": round(value, 4)})
    return {"pattern": pattern, "points": points, "noise": noise, "count": len(points)}


def math_sin(x):
    import math
    return math.sin(x)


@server.tool(description="Compute privacy budget consumption")
def privacy_budget(epsilon: float = 1.0, delta: float = 1e-5) -> dict:
    return {"epsilon": epsilon, "delta": delta, "interpretation": "moderate" if epsilon > 1 else "strict" if epsilon > 0.1 else "very_strict"}


@server.tool(description="Apply Laplace differential-privacy noise to a numeric value")
def differential_noise(value: float, epsilon: float = 1.0, sensitivity: float = 1.0) -> dict:
    import math
    scale = sensitivity / epsilon
    u = random.random() - 0.5
    noisy = value - scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
    return {"original": value, "noisy": round(noisy, 4), "epsilon": epsilon, "scale": round(scale, 4)}


if __name__ == "__main__":
    server.run()