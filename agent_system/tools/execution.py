"""Simulated effects: arbitrary action labels are recorded, never executed."""
from agent_system.protocol import POSITIVE, TEXT, object_schema
from agent_system.tools.base import ToolDefinition


def simulate_action(args, context):
    return {**args, "simulated_only": True,
            "committed": args["action"] != "reject"}, True


TOOLS = (
    ToolDefinition('simulate_action', 'If audit.allowed is false, submit action reject. Otherwise follow plan.action, plan.sku and plan.quantity. Destination is internal_inventory. No real external effects occur.',
        object_schema({"action": TEXT, "sku": TEXT, "quantity": POSITIVE, "destination": TEXT}), simulate_action),
)
