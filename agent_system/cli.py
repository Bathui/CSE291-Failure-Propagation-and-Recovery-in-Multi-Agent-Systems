"""Command-line parsing and reporting; role execution lives in the package modules."""
import argparse
import os
from pathlib import Path

from agent_system.domain.tasks import task_for, validate_task
from agent_system.experiments.runner import run_experiment
from agent_system.experiments.recovery import METHODS
from agent_system.experiments.settings import ExperimentSettings
from agent_system.faults.inventory import FAULTS
from agent_system.protocol import strict_json


def build_parser():
    defaults = ExperimentSettings()
    parser = argparse.ArgumentParser(
        prog="python -m agent_system",
        description="Run the four-role inventory agent experiment.")
    parser.add_argument("--base-url", default=os.environ.get("LLAMA_BASE_URL", defaults.base_url))
    parser.add_argument("--model", default=os.environ.get("LLAMA_MODEL", defaults.model))
    parser.add_argument("--tasks", type=int, default=3, help="Number of distinct built-in tasks (1-6)")
    parser.add_argument("--task-file", type=Path, help="JSON array of tasks, replacing built-in tasks")
    parser.add_argument("--repeats", type=int, default=defaults.repeats)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    parser.add_argument("--timeout", type=float, default=defaults.timeout)
    parser.add_argument("--max-tokens", type=int, default=defaults.max_tokens)
    parser.add_argument("--max-turns", type=int, default=defaults.max_turns)
    parser.add_argument("--output", type=Path, default=defaults.output)
    parser.add_argument("--fault", choices=("none", *FAULTS), default=defaults.fault,
                        help="Inject one fault into the Researcher output")
    parser.add_argument("--recovery", choices=METHODS, default=defaults.recovery)
    parser.add_argument("--suite", action="store_true", help="Run paired Phase 1 conditions")
    return parser


def report_run(record, repeat):
    metrics = record["metrics"]
    print("task=%s repeat=%s success=%s stages=%s calls=%s error=%s" % (
        record["task"]["id"], repeat, metrics["success"], metrics["completed_stages"],
        metrics["model_calls"], record["failure"]), flush=True)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = ExperimentSettings(**{name: getattr(args, name) for name in (
            "base_url", "model", "timeout", "max_tokens", "max_turns", "repeats", "seed", "output",
            "fault", "recovery")})
        if args.task_file:
            tasks = strict_json(args.task_file.read_text(encoding="utf-8"))
        else:
            if not 1 <= args.tasks <= 6:
                raise ValueError("--tasks must be 1-6; use --task-file for a larger task set")
            tasks = [task_for(index) for index in range(args.tasks)]
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("The task file must be a nonempty JSON array")
        for task in tasks:
            validate_task(task)
        if len({str(task["id"]) for task in tasks}) != len(tasks):
            raise ValueError("Task IDs must be unique")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.suite:
        if args.fault != "none" or args.recovery != "none":
            parser.error("--suite selects its own faults and recovery methods")
        from agent_system.experiments.suite import run_suite
        print("Suite results: " + str(run_suite(settings, tasks, report_run).resolve()))
        return 0
    result = run_experiment(settings, tasks, on_run=report_run)
    print("Results: " + str(result.output.resolve()))
    return 1 if result.has_errors else 0
