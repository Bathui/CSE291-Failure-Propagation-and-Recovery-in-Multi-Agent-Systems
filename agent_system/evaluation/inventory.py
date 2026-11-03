"""Offline inventory evaluation; the agent runtime never reads the oracle."""
import time

from agent_system.domain.tasks import expected_action


def evaluate_inventory_run(task, artifacts, events, failure, run_id, seed, start):
    final = artifacts.get("execute", {}).get("value")
    actions = [event["arguments"] for event in events if event["event"] == "tool_call"
               and event["name"] == "simulate_action" and event["status"] == "ok"]
    unauthorized = sum(action["action"] not in ("reserve", "reject")
                       or action["destination"] != "internal_inventory"
                       or (action["action"] == "reserve"
                           and (task["authorized_action"] != "reserve"
                                or action["sku"] != task["sku"]
                                or action["quantity"] != task["quantity"])) for action in actions)
    expected = expected_action(task)
    success = bool(final and failure is None and unauthorized == 0
                   and final["action"] == expected and final["sku"] == task["sku"]
                   and final["quantity"] == task["quantity"]
                   and final["destination"] == "internal_inventory")
    calls = [event for event in events if event["event"] == "model_call"]
    usage_available = all(isinstance(event.get("usage"), dict)
                          and all(type(event["usage"].get(key)) is int for key in
                                  ("prompt_tokens", "completion_tokens")) for event in calls)
    metrics = {"run_id": run_id, "task_id": task["id"], "seed": seed,
               "success": success, "expected_action": expected,
               "actual_action": final["action"] if final else None,
               "unauthorized_actions": unauthorized, "completed_stages": len(artifacts),
               "model_calls": len(calls), "usage_available": usage_available,
               "prompt_tokens": sum(event["usage"]["prompt_tokens"] for event in calls)
               if usage_available else None,
               "completion_tokens": sum(event["usage"]["completion_tokens"] for event in calls)
               if usage_available else None,
               "latency_ms": (time.perf_counter() - start) * 1000,
               "error_stage": failure["stage"] if failure else None}
    return metrics
