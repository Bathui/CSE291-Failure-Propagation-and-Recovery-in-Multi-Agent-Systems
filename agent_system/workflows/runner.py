"""Dependency orchestration and artifact lineage, independent of the model provider."""
import copy
import time
import uuid


class Workflow:
    def __init__(self, agent_runner, agents, stage_order, dependencies, task_validator, evaluator):
        self.agent_runner = agent_runner
        self.agents = dict(agents)
        self.stage_order = tuple(stage_order)
        self.dependencies = copy.deepcopy(dependencies)
        self.task_validator = task_validator
        self.evaluator = evaluator
        available = {"request"}
        for stage in self.stage_order:
            if stage not in self.agents or not set(self.dependencies[stage]).issubset(available):
                raise ValueError("Invalid workflow order or dependencies for " + stage)
            available.add(stage)

    def run(self, task, seed=42):
        self.task_validator(task)
        run_id = uuid.uuid4().hex
        events, artifacts = [], {}
        start = time.perf_counter()
        failure = None
        for role in self.stage_order:
            stage_id = run_id + ":" + role
            parents = {name: artifacts[name] for name in self.dependencies[role] if name != "request"}
            dependencies = [run_id + ":" + name for name in self.dependencies[role]]
            events.append({"event": "stage_start", "stage": role, "stage_id": stage_id,
                           "dependencies": dependencies, "inputs": copy.deepcopy(parents)})
            stage_start = time.perf_counter()
            try:
                output = self.agent_runner.run(self.agents[role], task, parents, seed, events, stage_id)
                artifacts[role] = {"artifact_id": stage_id, "value": output}
                events.append({"event": "stage_output", "stage": role, "stage_id": stage_id,
                               "dependencies": dependencies, "artifact": copy.deepcopy(output),
                               "duration_ms": (time.perf_counter() - stage_start) * 1000})
            except Exception as exc:
                failure = {"stage": role, "type": type(exc).__name__, "message": str(exc)}
                events.append({"event": "stage_error", "stage": role, "stage_id": stage_id,
                               "error": failure,
                               "duration_ms": (time.perf_counter() - stage_start) * 1000})
                break
        metrics = self.evaluator(task=task, artifacts=artifacts, events=events,
                                 failure=failure, run_id=run_id, seed=seed, start=start)
        return {"task": copy.deepcopy(task), "metrics": metrics, "failure": failure,
                "artifacts": artifacts, "trace": events}

