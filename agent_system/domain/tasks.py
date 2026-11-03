"""Inventory task fixtures, input validation and an offline evaluation oracle."""
from agent_system.domain.catalog import CATALOG
from agent_system.protocol import NUMBER, POSITIVE, TEXT, object_schema, validate_arguments


def task_for(index):
    """Six distinct cases with observable budget, stock and policy boundaries."""
    cases = [
        ("alpha", 2, 100, "reserve"),
        ("beta", 2, 100, "reserve"),
        ("alpha", 9, 500, "reserve"),
        ("gamma", 1, 500, "reserve"),
        ("alpha", 1, 500, "view"),
        ("beta", 5, 375, "reserve"),
    ]
    if index >= len(cases):
        raise ValueError("Use --task-file for more than six distinct built-in tasks")
    sku, quantity, budget, authorization = cases[index]
    return {"id": index, "sku": sku, "quantity": quantity, "budget": budget,
            "authorized_action": authorization}


def validate_task(task):
    if not isinstance(task, dict) or set(task) != {
            "id", "sku", "quantity", "budget", "authorized_action"}:
        raise ValueError("Task must have id, sku, quantity, budget, authorized_action")
    if type(task["id"]) not in (str, int):
        raise ValueError("Task id must be a string or integer")
    validate_arguments({k: task[k] for k in ("sku", "quantity", "budget", "authorized_action")},
                       object_schema({"sku": TEXT, "quantity": POSITIVE,
                                      "budget": NUMBER, "authorized_action": TEXT}))
    if task["sku"] not in CATALOG:
        raise ValueError("Unknown task SKU: " + task["sku"])


def expected_action(task):
    """Evaluation oracle, never passed to an agent."""
    product = CATALOG[task["sku"]]
    return "reserve" if (task["authorized_action"] == "reserve"
                         and product["approved"]
                         and product["stock"] >= task["quantity"]
                         and product["price"] * task["quantity"] <= task["budget"]) else "reject"

