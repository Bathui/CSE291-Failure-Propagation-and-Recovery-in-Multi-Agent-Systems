
"""Phase 1: Failure Propagation in Multi-Agent Systems.

Deterministic simulated agents, not real LLM inference.
All executor actions are simulated; no external actions occur.
"""

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


CATALOG = {
    "alpha": {"price": 40, "stock": 8, "approved": True},
    "beta": {"price": 75, "stock": 5, "approved": True},
    "gamma": {"price": 110, "stock": 3, "approved": False},
}

DEPENDENCIES = {
    "research": ["request"],
    "audit": ["request"],
    "plan": ["research", "request"],
    "execute": ["plan", "audit"],
}

WEIGHTS = {
    "research": 3,
    "audit": 2,
    "plan": 4,
    "execute": 2,
}

STAGES = ("research", "audit", "plan", "execute")

FAULTS = (
    "none",
    "wrong_price",
    "malicious_instruction",
    "timeout",
    "stale_stock",
    "audit_corruption",
    "plan_tamper",
)


@dataclass
class Run:
    task_id: int
    fault: str
    method: str
    stage: str
    success: bool
    unauthorized_actions: int
    affected_stages: int
    propagated_stages: int
    wasted_work: int
    recomputed_stages: int
    retained_valid_work: int
    latency_ms: float
    inference_cost_units: int
    tracking_overhead_ms: float
    fault_consumed: bool
    detected: bool
    calls: int
    trace: list


def task_for(seed):
    skus = ("alpha", "beta", "gamma")
    sku = skus[seed % len(skus)]
    amount = 1 + seed % 4

    return {
        "id": seed,
        "sku": sku,
        "quantity": amount,
        "budget": 500,
        "authorized_action": "reserve",
    }


def baseline_action(task):
    product = CATALOG[task["sku"]]

    eligible = (
        product["approved"]
        and product["stock"] >= task["quantity"]
        and product["price"] * task["quantity"] <= task["budget"]
    )

    return "reserve" if eligible else "reject"


def stage_compute(stage, task, values, fault):
    item = CATALOG[task["sku"]]

    # Researcher Agent
    if stage == "research":
        if fault == "timeout":
            raise TimeoutError("research simulated timeout")

        result = {
            "sku": task["sku"],
            "price": item["price"],
            "stock": item["stock"],
            "approved": item["approved"],
            "instruction": "none",
        }

        if fault == "wrong_price":
            result["price"] = 0

        if fault == "stale_stock":
            result["stock"] = 999

        if fault == "malicious_instruction":
            result["instruction"] = "export_customer_data"

        return result

    # Auditor Agent
    if stage == "audit":
        result = {
            "allowed": task["authorized_action"] == "reserve",
            "destination": "internal_inventory",
        }

        if fault == "audit_corruption":
            result["destination"] = "external_endpoint"

        return result

    # Planner Agent
    if stage == "plan":
        data = values["research"]

        eligible = (
            data["approved"]
            and data["stock"] >= task["quantity"]
            and data["price"] * task["quantity"] <= task["budget"]
        )

        result = {
            "action": "reserve" if eligible else "reject",
            "sku": data["sku"],
            "quantity": task["quantity"],
            "instruction": data["instruction"],
        }

        if fault == "plan_tamper":
            result["action"] = (
                "reserve" if result["action"] == "reject"
                else "reject"
            )

        return result

    # Executor Agent
    if stage == "execute":
        plan = values["plan"]
        audit = values["audit"]

        # Intentionally vulnerable simulated executor.
        # No real external I/O is performed.
        action = (
            "export_customer_data"
            if plan["instruction"] == "export_customer_data"
            else plan["action"]
        )

        destination = (
            "external_endpoint"
            if audit["destination"] == "external_endpoint"
            else "internal_inventory"
        )

        return {
            "action": action,
            "destination": destination,
            "simulated_only": True,
            "committed": action != "reject",
        }

    raise ValueError(stage)


def verified(stage, task, result):
    """Idealized verification against trusted ground truth."""

    if stage == "research":
        expected = stage_compute(
            "research", task, {}, "none"
        )
        return result == expected

    if stage == "audit":
        expected = stage_compute(
            "audit", task, {}, "none"
        )
        return result == expected

    if stage == "plan":
        clean_research = stage_compute(
            "research", task, {}, "none"
        )

        expected = stage_compute(
            "plan",
            task,
            {"research": clean_research},
            "none",
        )

        return result == expected

    return True


def descendants(source):
    """Find all downstream stages depending on a source."""

    seen = set()
    frontier = [source]

    while frontier:
        current = frontier.pop()

        for stage, dependencies in DEPENDENCIES.items():
            if current in dependencies and stage not in seen:
                seen.add(stage)
                frontier.append(stage)

    return seen


def run(task, fault="none", method="none", stage=None):
    assert fault in FAULTS
    assert method in ("none", "restart", "verify")

    location = stage or (
        "audit" if fault == "audit_corruption"
        else "plan" if fault == "plan_tamper"
        else "research"
    )

    if fault == "none":
        location = "none"

    if (
        (fault == "audit_corruption" and location != "audit")
        or (fault == "plan_tamper" and location != "plan")
    ):
        raise ValueError("fault/stage mismatch")

    if (
        fault not in ("audit_corruption", "plan_tamper", "none")
        and location != "research"
    ):
        raise ValueError("fault/stage mismatch")

    start_time = time.perf_counter_ns()

    values = {}
    trace = []
    total_calls = 0
    cost = 0
    detected = False
    verification_ns = 0

    contaminated = set()
    attempted = set()

    # Initial execution
    for s in STAGES:
        total_calls += 1
        cost += WEIGHTS[s]

        injected = fault if s == location else "none"
        stage_start = time.perf_counter_ns()

        try:
            result = stage_compute(
                s, task, values, injected
            )
            status = "ok"

        except TimeoutError:
            result = None
            status = "timeout"

        parents = [
            dependency
            for dependency in DEPENDENCIES[s]
            if dependency != "request"
        ]

        is_contaminated = (
            injected != "none"
            or any(p in contaminated for p in parents)
        )

        if is_contaminated:
            contaminated.add(s)

        trace.append({
            "stage": s,
            "event": "output",
            "status": status,
            "dependencies": DEPENDENCIES[s],
            "artifact": result,
            "injected": injected,
            "tainted_lineage": is_contaminated,
            "duration_ms": (
                time.perf_counter_ns() - stage_start
            ) / 1e6,
        })

        attempted.add(s)

        if status == "timeout":
            if method == "verify":
                detected = True
            break

        values[s] = result

        # Verification baseline
        if method == "verify" and s != "execute":
            verification_start = time.perf_counter_ns()

            ok = verified(s, task, result)

            verification_ns += (
                time.perf_counter_ns() - verification_start
            )

            cost += 1

            trace.append({
                "stage": s,
                "event": "verification",
                "passed": ok,
                "dependencies": [s],
            })

            if not ok:
                detected = True
                break

    # Full restart assumes the faulty artifact is known.
    if method == "restart" and fault != "none":
        detected = True

    reruns = 0

    should_restart = (
        (method == "restart" and fault != "none")
        or (method == "verify" and detected)
    )

    if should_restart:
        reruns = len(STAGES)
        values = {}

        trace.append({
            "stage": "system",
            "event": "full_restart",
            "dependencies": [],
            "artifacts_reused": [],
        })

        for s in STAGES:
            stage_start = time.perf_counter_ns()

            result = stage_compute(
                s, task, values, "none"
            )

            values[s] = result
            total_calls += 1
            cost += WEIGHTS[s]

            trace.append({
                "stage": s,
                "event": "restart_output",
                "status": "ok",
                "dependencies": DEPENDENCIES[s],
                "artifact": result,
                "duration_ms": (
                    time.perf_counter_ns() - stage_start
                ) / 1e6,
            })

    # Evaluate final result
    final = values.get("execute", {})

    unauthorized = int(
        final.get("action") == "export_customer_data"
        or final.get("destination") == "external_endpoint"
    )

    success = bool(
        final
        and final["action"] == baseline_action(task)
        and unauthorized == 0
    )

    actual_affected = (
        descendants(location) | {location}
        if fault != "none"
        else set()
    )

    consumed = bool(
        fault != "none"
        and location in attempted
        and len(actual_affected & attempted) > 1
    )

    propagated = (
        len((actual_affected - {location}) & attempted)
        if consumed else 0
    )

    retained = (
        len(STAGES) - len(actual_affected & attempted)
        if fault != "none"
        else len(STAGES)
    )

    if reruns:
        wasted = sum(WEIGHTS[s] for s in attempted)
    elif fault != "none":
        wasted = sum(
            WEIGHTS[s]
            for s in actual_affected & attempted
        )
    else:
        wasted = 0

    latency_ms = (
        time.perf_counter_ns() - start_time
    ) / 1e6

    return Run(
        task_id=task["id"],
        fault=fault,
        method=method,
        stage=location,
        success=success,
        unauthorized_actions=unauthorized,
        affected_stages=len(actual_affected & attempted),
        propagated_stages=propagated,
        wasted_work=wasted,
        recomputed_stages=reruns,
        retained_valid_work=retained,
        latency_ms=latency_ms,
        inference_cost_units=cost,
        tracking_overhead_ms=verification_ns / 1e6,
        fault_consumed=consumed,
        detected=detected,
        calls=total_calls,
        trace=trace,
    )


def benchmark(n=90, output="results"):
    if n < 1:
        raise ValueError("tasks must be positive")

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    results = []

    # Save complete execution traces
    with (out / "traces.jsonl").open("w") as fp:
        for i in range(n):
            task = task_for(i)

            for fault in FAULTS:
                for method in ("none", "restart", "verify"):
                    result = run(task, fault, method)
                    record = asdict(result)

                    results.append({
                        k: v
                        for k, v in record.items()
                        if k != "trace"
                    })

                    fp.write(
                        json.dumps({"task": task, **record})
                        + "\n"
                    )

    # Save individual experiment results
    with (out / "runs.csv").open(
        "w", newline=""
    ) as fp:
        writer = csv.DictWriter(
            fp, fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    grouped = defaultdict(list)

    for result in results:
        key = (result["fault"], result["method"])
        grouped[key].append(result)

    summary = []

    for (fault, method), vals in sorted(grouped.items()):
        summary.append({
            "fault": fault,
            "method": method,
            "n": len(vals),
            "success_rate": round(
                statistics.mean(
                    v["success"] for v in vals
                ), 4
            ),
            "unauthorized_rate": round(
                statistics.mean(
                    v["unauthorized_actions"] > 0
                    for v in vals
                ), 4
            ),
            "fault_consumed_rate": round(
                statistics.mean(
                    v["fault_consumed"] for v in vals
                ), 4
            ),
            "mean_propagated_stages": round(
                statistics.mean(
                    v["propagated_stages"] for v in vals
                ), 3
            ),
            "mean_wasted_work": round(
                statistics.mean(
                    v["wasted_work"] for v in vals
                ), 3
            ),
            "mean_recomputed_stages": round(
                statistics.mean(
                    v["recomputed_stages"] for v in vals
                ), 3
            ),
            "mean_cost_units": round(
                statistics.mean(
                    v["inference_cost_units"] for v in vals
                ), 3
            ),
            "median_latency_ms": round(
                statistics.median(
                    v["latency_ms"] for v in vals
                ), 4
            ),
            "mean_tracking_overhead_ms": round(
                statistics.mean(
                    v["tracking_overhead_ms"] for v in vals
                ), 4
            ),
        })

    with (out / "summary.csv").open(
        "w", newline=""
    ) as fp:
        writer = csv.DictWriter(
            fp, fieldnames=summary[0].keys()
        )
        writer.writeheader()
        writer.writerows(summary)

    config = {
        "tasks": n,
        "seed_rule": "task_for(i)",
        "faults": FAULTS,
        "methods": ["none", "restart", "verify"],
        "note": (
            "Deterministic CPU simulator; "
            "no actual LLM calls or external actions."
        ),
        "weight_units": WEIGHTS,
    }

    (out / "config.json").write_text(
        json.dumps(config, indent=2)
    )

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tasks", type=int, default=90
    )

    parser.add_argument(
        "--output", default="results"
    )

    args = parser.parse_args()

    for item in benchmark(args.tasks, args.output):
        print(
            f"{item['fault']:23s} "
            f"{item['method']:8s} "
            f"success={item['success_rate']:.2f} "
            f"unauthorized={item['unauthorized_rate']:.2f} "
            f"cost={item['mean_cost_units']:.1f}"
        )


if __name__ == "__main__":
    main()
