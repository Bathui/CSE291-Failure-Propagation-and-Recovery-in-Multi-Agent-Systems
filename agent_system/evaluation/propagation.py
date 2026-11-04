"""Compare paired clean, injected, and recovered traces."""


def semantic_output(artifact):
    return {k: v for k, v in artifact["value"].items() if k != "source_id"}


def compare(clean, run):
    initial = run.get("discarded_attempt", run)
    events = initial["trace"]
    injection = next((e for e in events if e["event"] == "fault_injection"), None)
    reached = []
    if injection and injection["changed"] and "field" in injection:
        for event in events:
            if event["event"] != "stage_start":
                continue
            parent = event["inputs"].get(injection["stage"])
            if parent and parent["artifact_id"] == injection["stage_id"]:
                reached.append(event["stage"])

    clean_artifacts = clean["artifacts"]
    changed = [
        stage for stage, artifact in initial["artifacts"].items()
        if stage in clean_artifacts
        and semantic_output(artifact) != semantic_output(clean_artifacts[stage])
    ]
    missing = [stage for stage in clean_artifacts if stage not in initial["artifacts"]]
    clean_calculation = calculation(clean)
    injected_calculation = calculation(initial)
    clean_metrics, first_metrics, metrics = clean["metrics"], initial["metrics"], run["metrics"]
    return {
        "task_id": metrics["task_id"], "seed": metrics["seed"],
        "injection": injection, "direct_consumers": reached,
        "changed_artifact_stages": changed, "missing_artifact_stages": missing,
        "clean_calculation": clean_calculation, "first_calculation": injected_calculation,
        "calculation_changed": (clean_calculation is not None and injected_calculation is not None
                                and clean_calculation != injected_calculation),
        "clean_action": clean_metrics["actual_action"], "first_action": first_metrics["actual_action"],
        "clean_success": clean_metrics["success"], "first_success": first_metrics["success"],
        "new_failure_before_recovery": clean_metrics["success"] and not first_metrics["success"],
        "latency_delta_ms": metrics["latency_ms"] - clean_metrics["latency_ms"],
        "model_call_delta": metrics["model_calls"] - clean_metrics["model_calls"],
        "metrics": metrics,
    }


def calculation(run):
    return next((e["result"] for e in reversed(run["trace"])
                 if e["event"] == "tool_call" and e["name"] == "calculate_total"
                 and e["status"] == "ok"), None)
