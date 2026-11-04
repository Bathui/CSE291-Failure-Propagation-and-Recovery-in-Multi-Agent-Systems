"""Scripted model fixtures for offline orchestration tests."""
import copy
import json


def tool_response(name, arguments, identifier="call-1"):
    return {"choices": [{"finish_reason": "tool_calls", "message": {
        "role": "assistant", "content": None, "tool_calls": [{
            "id": identifier, "type": "function", "function": {
                "name": name, "arguments": json.dumps(arguments)}}]}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10}}


class FixtureClient:
    """Choose scripted tool calls to test orchestration, not model reasoning."""
    def __init__(self):
        self.inputs = []

    def preflight(self):
        return {"data": [{"id": "cse291-qwen3-8b"}]}

    def chat(self, messages, tools, seed):
        self.inputs.append(copy.deepcopy(messages))
        visible = json.loads(messages[1]["content"])
        names = [tool["function"]["name"] for tool in tools]
        observed = [json.loads(message["content"]) for message in messages if message["role"] == "tool"]
        if "lookup_product" in names:
            if not observed:
                return tool_response("lookup_product", {"sku": visible["request"]["sku"]})
            return tool_response("finish_research", observed[-1])
        if "check_permission" in names:
            if not observed:
                return tool_response("check_permission", {})
            return tool_response("finish_audit", observed[-1])
        if "finish_plan" in names:
            task = visible["request"]
            if not observed:
                return tool_response("calculate_total", {"unit_price": visible["research"]["price"],
                                     "quantity": task["quantity"]})
            return tool_response("finish_plan", {"action": "reserve", "sku": task["sku"],
                                 "quantity": task["quantity"], "instruction": "none"})
        plan = visible["plan"]
        return tool_response("simulate_action", {"action": plan["action"], "sku": plan["sku"],
                             "quantity": plan["quantity"], "destination": "internal_inventory"})
