"""Run and compare the Phase 1 experiment matrix."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from agent_system.evaluation.propagation import compare
from agent_system.experiments.recovery import METHODS
from agent_system.experiments.runner import run_experiment
from agent_system.faults.inventory import FAULTS


def run_suite(settings, tasks, on_run=None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = settings.output / ("phase1-" + stamp + "-" + uuid4().hex[:8])
    root.mkdir(parents=True, exist_ok=False)
    clean = {}
    conditions = []
    for fault in ("none", *FAULTS):
        for method in METHODS:
            print(f"Condition: fault={fault} recovery={method}", flush=True)
            result = run_experiment(replace(settings, output=root, fault=fault, recovery=method),
                                    tasks, on_run=on_run)
            with (result.output / "traces.jsonl").open(encoding="utf-8") as traces:
                records = [json.loads(line) for line in traces]
            paired = []
            for record in records:
                metrics = record["metrics"]
                key = (metrics["task_id"], metrics["seed"])
                if fault == method == "none":
                    clean[key] = record
                paired.append(compare(clean[key], record))
            conditions.append({"fault": fault, "category": FAULTS[fault].category if fault in FAULTS
                               else "clean", "recovery": method, "run_directory": result.output.name,
                               "summary": result.summary, "pairs": paired})
            (root / "comparison.json").write_text(json.dumps(conditions, indent=2), encoding="utf-8")
    return root
