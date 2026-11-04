"""Application-level experiment execution; progress reporting is injectable."""
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

from agent_system.clients.llama_cpp import LlamaCppClient
from agent_system.domain.tasks import validate_task
from agent_system.experiments.storage import ResultWriter
from agent_system.experiments.recovery import run_with_recovery
from agent_system.faults.inventory import FAULTS
from agent_system.scenarios.inventory import AGENTS, build_inventory_registry, build_inventory_workflow
from agent_system.workflows.definitions import DEPENDENCIES


@dataclass(frozen=True)
class ExperimentResult:
    output: Path
    summary: dict
    has_errors: bool


def run_experiment(settings, tasks, client=None, on_run=None):
    fault = None if settings.fault == "none" else FAULTS[settings.fault]
    transform_output = partial(fault.apply, name=settings.fault) if fault else None
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Tasks must be a nonempty list")
    for task in tasks:
        validate_task(task)
    if len({str(task["id"]) for task in tasks}) != len(tasks):
        raise ValueError("Task IDs must be unique")
    if client is None:
        client = LlamaCppClient(settings.base_url, settings.model, settings.timeout, settings.max_tokens)
    server_info = client.preflight()
    workflow = build_inventory_workflow(client, settings.max_turns)
    config = {"backend": "llama.cpp", "base_url": settings.base_url, "model": settings.model,
              "temperature": 0, "thinking": False, "max_tokens": settings.max_tokens,
              "max_turns": settings.max_turns, "timeout": settings.timeout, "seed": settings.seed,
              "repeats": settings.repeats, "tasks": tasks, "dependencies": DEPENDENCIES,
              "prompts": {name: agent.prompt for name, agent in AGENTS.items()},
              "tool_schemas": build_inventory_registry().schemas(), "server_info": server_info,
              "fault": {"name": settings.fault, **asdict(fault)} if fault else {"name": "none"},
              "recovery": settings.recovery,
              "scope": "Four real LLM roles; simulated effects and one-shot faults."}
    with ResultWriter(settings.output) as writer:
        writer.write_config(config)
        for repeat in range(settings.repeats):
            for task in tasks:
                record = run_with_recovery(workflow, task, settings.seed + repeat,
                                           transform_output, settings.recovery)
                writer.write_record(record)
                if on_run is not None:
                    on_run(record, repeat)
        summary = writer.finish()
        has_errors = any(row["error_stage"] for row in writer.metrics)
        return ExperimentResult(writer.path, summary, has_errors)
