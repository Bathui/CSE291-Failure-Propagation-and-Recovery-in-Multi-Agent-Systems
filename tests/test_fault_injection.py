"""Check that an injected artifact reaches the live workflow's tool boundary."""
import json
import unittest
from functools import partial

from agent_system.domain.tasks import task_for
from agent_system.evaluation.propagation import compare
from agent_system.experiments.recovery import run_with_recovery
from agent_system.faults.inventory import FAULTS
from agent_system.scenarios.inventory import build_inventory_workflow
from tests.helpers import FixtureClient, tool_response


class FaultInjectionTests(unittest.TestCase):
    def test_wrong_executor_action_triggers_one_retry_and_preserves_first_action(self):
        class ExecutorFixture(FixtureClient):
            def __init__(self, correct_on_retry):
                super().__init__()
                self.correct_on_retry = correct_on_retry
                self.executions = 0

            def chat(self, messages, tools, seed):
                if tools[0]["function"]["name"] != "simulate_action":
                    return super().chat(messages, tools, seed)
                self.executions += 1
                action = "reject" if self.correct_on_retry and self.executions > 1 else "reserve"
                return tool_response("simulate_action", {"action": action, "sku": "alpha",
                                     "quantity": 1, "destination": "internal_inventory"})

        for method in ("none", "restart", "verify"):
            with self.subTest(method=method):
                workflow = build_inventory_workflow(ExecutorFixture(True))
                result = run_with_recovery(workflow, task_for(4), 42, None, method)
                self.assertEqual(result["metrics"]["restarted"], method != "none")
                self.assertEqual(result["metrics"]["success"], method != "none")
                self.assertEqual(result["metrics"]["unauthorized_actions"], 1)
                if method != "none":
                    first = result["discarded_attempt"]
                    self.assertEqual(first["metrics"]["actual_action"], "reserve")
                    self.assertEqual(first["failure"]["stage"], "execute")
                    self.assertEqual(result["metrics"]["actual_action"], "reject")

        workflow = build_inventory_workflow(ExecutorFixture(False))
        result = run_with_recovery(workflow, task_for(4), 42, None, "restart")
        self.assertFalse(result["metrics"]["success"])
        self.assertEqual(result["metrics"]["error_stage"], "execute")
        self.assertEqual(result["metrics"]["unauthorized_actions"], 2)

    def test_verification_contains_fault_before_consumption_and_accounts_for_retry(self):
        task = task_for(0)
        workflow = build_inventory_workflow(FixtureClient())
        fault = partial(FAULTS["wrong-price"].apply, name="wrong-price")
        clean = run_with_recovery(workflow, task, 42, None, "none")
        restart = run_with_recovery(workflow, task, 42, fault, "restart")
        verify = run_with_recovery(workflow, task, 42, fault, "verify")

        self.assertEqual(compare(clean, restart)["direct_consumers"], ["plan"])
        self.assertEqual(compare(clean, verify)["direct_consumers"], [])
        self.assertEqual(restart["metrics"]["discarded_model_calls"], 7)
        self.assertEqual(verify["metrics"]["discarded_model_calls"], 2)
        for run in (restart, verify):
            self.assertTrue(run["metrics"]["success"])
            self.assertEqual(run["artifacts"]["research"]["value"]["price"], 40)
            self.assertEqual(run["metrics"]["model_calls"],
                             clean["metrics"]["model_calls"] + run["metrics"]["discarded_model_calls"])

    def test_stale_stock_changes_planner_evidence_but_not_expected_action(self):
        client = FixtureClient()
        workflow = build_inventory_workflow(client)
        task = task_for(2)
        clean = workflow.run(task)
        fault = partial(FAULTS["stale-stock"].apply, name="stale-stock")
        injected = workflow.run(task, transform_output=fault)
        for run, expected_stock, expected_check in ((clean, 8, False), (injected, 10, True)):
            planner = next(e for e in run["trace"] if e["event"] == "model_call" and e["stage"] == "plan")
            visible = json.loads(planner["messages"][1]["content"])
            self.assertEqual(visible["research"]["stock"], expected_stock)
            calculation = next(e for e in run["trace"] if e.get("name") == "calculate_total")
            self.assertIs(calculation["result"]["stock_ok"], expected_check)
            self.assertEqual(run["metrics"]["expected_action"], "reject")
