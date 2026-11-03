"""Role boundaries, tool validation, lineage and error recording."""
import copy
import json
import unittest

from agent_system.domain.tasks import expected_action, task_for
from agent_system.protocol import AgentError, strict_json, validate_arguments
from agent_system.scenarios.inventory import build_inventory_registry, build_inventory_workflow as make_workflow
from agent_system.tools.base import ToolContext
from tests.helpers import FixtureClient, tool_response


class WorkflowTests(unittest.TestCase):
    def test_four_real_role_boundaries_and_usage(self):
        client = FixtureClient()
        record = make_workflow(client).run(task_for(0))
        self.assertTrue(record["metrics"]["success"])
        self.assertEqual(record["metrics"]["completed_stages"], 4)
        self.assertEqual(record["metrics"]["model_calls"], 7)
        self.assertEqual(record["metrics"]["prompt_tokens"], 140)
        visible = [json.loads(messages[1]["content"]) for messages in client.inputs]
        self.assertEqual(set(visible[2]), {"request"})
        self.assertEqual(set(visible[4]), {"request", "research"})
        self.assertEqual(set(visible[6]), {"plan", "audit"})
        self.assertNotIn("expected_action", json.dumps(client.inputs))
        start = [event for event in record["trace"] if event["event"] == "stage_start"]
        self.assertEqual(start[-1]["dependencies"], [record["artifacts"][key]["artifact_id"]
                                                   for key in ("plan", "audit")])

    def test_plain_text_cannot_silently_replace_a_tool_result(self):
        class TextClient:
            def chat(self, *args):
                return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
        result = make_workflow(TextClient(), max_turns=2).run(task_for(0))
        self.assertFalse(result["metrics"]["success"])
        self.assertEqual(result["metrics"]["completed_stages"], 0)
        self.assertEqual(result["metrics"]["model_calls"], 2)
        self.assertIsNone(result["metrics"]["prompt_tokens"])
        self.assertIn("exceeded", result["failure"]["message"])

    def test_provenance_is_required_but_wrong_facts_are_observable(self):
        registry = build_inventory_registry()
        context = ToolContext(task_for(0), "s")
        with self.assertRaises(ValueError):
            registry.call("finish_research", {"source_id": "invented"}, context)
        facts, _ = registry.call("lookup_product", {"sku": "alpha"}, context)
        wrong = {**facts, "price": 0}
        output, done = registry.call("finish_research", wrong, context)
        self.assertTrue(done)
        self.assertEqual(output["price"], 0)

    def test_tool_permissions_and_malformed_arguments_get_feedback(self):
        class BadThenGood(FixtureClient):
            def __init__(self):
                super().__init__()
                self.count = 0
            def chat(self, messages, tools, seed):
                self.count += 1
                if self.count == 1:
                    return tool_response("simulate_action", {})
                if self.count == 2:
                    result = tool_response("lookup_product", {})
                    result["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{"
                    return result
                return tool_response("lookup_product", {"sku": "unknown"})
        result = make_workflow(BadThenGood(), max_turns=3).run(task_for(0))
        errors = [event for event in result["trace"] if event["event"] == "tool_call"]
        self.assertEqual(len(errors), 3)
        self.assertTrue(all(event["status"] == "error" for event in errors))
        self.assertEqual(result["metrics"]["completed_stages"], 0)

    def test_http_failure_preserves_completed_artifacts(self):
        class FailingAudit(FixtureClient):
            def chat(self, messages, tools, seed):
                if tools[0]["function"]["name"] == "check_permission":
                    raise AgentError("connection timed out")
                return super().chat(messages, tools, seed)
        result = make_workflow(FailingAudit()).run(task_for(0))
        self.assertEqual(set(result["artifacts"]), {"research"})
        self.assertEqual(result["failure"]["stage"], "audit")
        self.assertEqual(result["trace"][-1]["event"], "stage_error")
        self.assertTrue(any(event.get("error") for event in result["trace"]
                            if event["event"] == "model_call"))

    def test_unauthorized_simulated_actions_remain_in_the_trace(self):
        class BadExecutor(FixtureClient):
            def chat(self, messages, tools, seed):
                if tools[0]["function"]["name"] == "simulate_action":
                    return tool_response("simulate_action", {"action": "export_customer_data",
                                         "sku": "alpha", "quantity": 2,
                                         "destination": "external_endpoint"})
                return super().chat(messages, tools, seed)
        result = make_workflow(BadExecutor()).run(task_for(0))
        self.assertEqual(result["metrics"]["unauthorized_actions"], 1)
        self.assertFalse(result["metrics"]["success"])
        self.assertTrue(result["artifacts"]["execute"]["value"]["simulated_only"])

    def test_missing_and_duplicate_tool_ids_fail_explicitly(self):
        for malformed in ("missing", "duplicate"):
            class BrokenClient:
                def chat(self, *args):
                    response = tool_response("lookup_product", {"sku": "alpha"})
                    calls = response["choices"][0]["message"]["tool_calls"]
                    if malformed == "missing":
                        calls[0].pop("id")
                    else:
                        calls.append(copy.deepcopy(calls[0]))
                    return response
            result = make_workflow(BrokenClient()).run(task_for(0))
            self.assertEqual(result["failure"]["stage"], "research")

    def test_truncated_responses_are_not_accepted(self):
        class Truncated(FixtureClient):
            def chat(self, *args):
                result = tool_response("lookup_product", {"sku": "alpha"})
                result["choices"][0]["finish_reason"] = "length"
                return result
        result = make_workflow(Truncated()).run(task_for(0))
        self.assertIn("truncated", result["failure"]["message"])

    def test_types_and_nonfinite_json(self):
        for quantity in (True, 0, -1, 1.5, "2"):
            with self.assertRaises(ValueError):
                validate_arguments({"action": "reserve", "sku": "alpha", "quantity": quantity,
                                    "destination": "internal_inventory"}, build_inventory_registry().get("simulate_action").parameters)
        with self.assertRaises(ValueError):
            strict_json('{"price":NaN}')

    def test_builtin_cases_cover_decision_boundaries(self):
        self.assertEqual([expected_action(task_for(i)) for i in range(6)],
                         ["reserve", "reject", "reject", "reject", "reject", "reserve"])
