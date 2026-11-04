"""One-shot recovery policies and accounting for discarded attempts."""
import time

from agent_system.evaluation.verification import verify_execution, verify_intermediate


METHODS = ("none", "restart", "verify")
INTERMEDIATE = ("research", "audit", "plan")


class VerificationError(ValueError):
    """An intermediate artifact failed independent verification."""


def check(stage, output, task, events, stage_id):
    started = time.perf_counter()
    mismatches = verify_intermediate(stage, output, task)
    events.append({"event": "verification", "stage": stage, "stage_id": stage_id,
                   "mismatches": mismatches,
                   "duration_ms": (time.perf_counter() - started) * 1000})
    return mismatches


def check_execution(attempt):
    artifacts = attempt["artifacts"]
    if "execute" not in artifacts:
        return
    started = time.perf_counter()
    artifact = artifacts["execute"]
    mismatches = verify_execution(artifact["value"], artifacts["plan"]["value"],
                                  artifacts["audit"]["value"])
    attempt["trace"].append({
        "event": "verification", "stage": "execute", "stage_id": artifact["artifact_id"],
        "mismatches": mismatches, "duration_ms": (time.perf_counter() - started) * 1000,
    })
    if mismatches:
        attempt["failure"] = {"stage": "execute", "type": "VerificationError",
                              "message": "Executor output mismatch: " + ", ".join(mismatches)}
        attempt["metrics"].update(success=False, error_stage="execute")


def run_with_recovery(workflow, task, seed, inject, method):
    started = time.perf_counter()

    def transform(stage, output, events, stage_id, injection):
        output = injection(stage, output, events, stage_id) if injection else output
        if method == "verify" and stage in INTERMEDIATE:
            if check(stage, output, task, events, stage_id):
                raise VerificationError("Intermediate artifact failed verification")
        return output

    first = workflow.run(task, seed, lambda *args: transform(*args, inject))
    detected = bool(first["failure"])
    if method == "restart" and not detected:
        for stage in INTERMEDIATE:
            artifact = first["artifacts"][stage]
            detected |= bool(check(stage, artifact["value"], task, first["trace"],
                                   artifact["artifact_id"]))
    if method != "none":
        check_execution(first)
        detected |= bool(first["failure"])

    attempts = [first]
    if method != "none" and detected:
        retry = workflow.run(task, seed, lambda *args: transform(*args, None))
        check_execution(retry)
        attempts.append(retry)

    final = attempts[-1]
    metrics = dict(final["metrics"])
    for key in ("model_calls", "unauthorized_actions"):
        metrics[key] = sum(attempt["metrics"][key] for attempt in attempts)
    metrics["usage_available"] = all(a["metrics"]["usage_available"] for a in attempts)
    for key in ("prompt_tokens", "completion_tokens"):
        metrics[key] = (sum(a["metrics"][key] for a in attempts)
                        if metrics["usage_available"] else None)
    verifications = [e for a in attempts for e in a["trace"] if e["event"] == "verification"]
    metrics.update(
        latency_ms=(time.perf_counter() - started) * 1000,
        recovery=method,
        restarted=len(attempts) == 2,
        discarded_model_calls=sum(a["metrics"]["model_calls"] for a in attempts[:-1]),
        discarded_stages=sum(a["metrics"]["completed_stages"] for a in attempts[:-1]),
        verification_checks=len(verifications),
        verification_ms=sum(e["duration_ms"] for e in verifications),
        verification_model_calls=0,
    )
    result = {**final, "metrics": metrics}
    if len(attempts) == 2:
        result["discarded_attempt"] = first
    return result
