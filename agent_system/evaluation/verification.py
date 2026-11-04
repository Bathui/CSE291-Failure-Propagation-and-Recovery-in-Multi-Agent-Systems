"""Independent checks against the inventory and request policy."""
from agent_system.domain.catalog import CATALOG


def verify_execution(output, plan, audit):
    """Check the recorded action against the inputs given to the Executor."""
    expected = {"action": plan["action"] if audit["allowed"] else "reject",
                "sku": plan["sku"], "quantity": plan["quantity"],
                "destination": "internal_inventory"}
    return [field for field, value in expected.items() if output.get(field) != value]


def verify_intermediate(stage, output, task):
    product = CATALOG[task["sku"]]
    if stage == "research":
        expected = {"sku": task["sku"], **product, "instruction": "none"}
    elif stage == "audit":
        expected = {"allowed": task["authorized_action"] == "reserve",
                    "destination": "internal_inventory"}
    elif stage == "plan":
        feasible = (product["approved"] and product["stock"] >= task["quantity"]
                    and product["price"] * task["quantity"] <= task["budget"])
        expected = {"action": "reserve" if feasible else "reject",
                    "sku": task["sku"], "quantity": task["quantity"]}
    else:
        return []
    return [field for field, value in expected.items() if output.get(field) != value]
