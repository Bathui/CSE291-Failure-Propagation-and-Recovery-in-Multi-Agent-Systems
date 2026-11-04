"""Arithmetic assistance and plan submission; no hidden-answer checks."""
import copy
import math

from agent_system.protocol import NUMBER, POSITIVE, TEXT, object_schema
from agent_system.tools.base import ToolDefinition


def calculate_total(args, context):
    result = {"total_price": args["unit_price"] * args["quantity"]}
    if not math.isfinite(result["total_price"]):
        raise ValueError("Calculated price is not finite")
    result["stock_ok"] = context.task["quantity"] <= context.inputs["research"]["stock"]
    context.evidence["calculation"] = result
    return result, False


def finish_plan(args, context):
    if "calculation" not in context.evidence:
        raise ValueError("Call calculate_total before submitting the plan")
    return copy.deepcopy(args), True


TOOLS = (
    ToolDefinition('calculate_total', 'Calculate total price and return stock_ok based on reported stock. Use before finish_plan.',
        object_schema({"unit_price": NUMBER, "quantity": POSITIVE}), calculate_total),
    ToolDefinition('finish_plan', 'After calculate_total: reserve only when research.approved is true, stock_ok is true, and total_price <= request.budget. Otherwise reject. Submit the requested SKU and quantity.',
        object_schema({"action": TEXT, "sku": TEXT, "quantity": POSITIVE, "instruction": TEXT}), finish_plan),
)
