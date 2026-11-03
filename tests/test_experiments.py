"""Application persistence and package entry-point checks without a live model."""
import contextlib
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_system.cli import main
from agent_system.domain.tasks import task_for
from agent_system.experiments.runner import run_experiment
from agent_system.experiments.settings import ExperimentSettings
from tests.helpers import FixtureClient


class ExperimentTests(unittest.TestCase):
    def test_experiment_writes_reproducible_inputs_traces_and_metrics(self):
        client = FixtureClient()
        progress = []
        with tempfile.TemporaryDirectory(prefix="cse291-experiment-") as directory:
            settings = ExperimentSettings(output=Path(directory), repeats=2)
            result = run_experiment(settings, [task_for(0)], client=client,
                                    on_run=lambda record, repeat: progress.append(repeat))
            self.assertEqual(progress, [0, 1])
            self.assertEqual(result.summary["runs"], 2)
            self.assertEqual(result.summary["model_calls"], 14)
            self.assertFalse(result.has_errors)
            self.assertEqual({path.name for path in result.output.iterdir()},
                             {"config.json", "traces.jsonl", "runs.csv", "summary.json"})
            config = json.loads((result.output / "config.json").read_text())
            records = [json.loads(line) for line in
                       (result.output / "traces.jsonl").read_text().splitlines()]
            with (result.output / "runs.csv").open(newline="") as fp:
                metrics = list(csv.DictReader(fp))
            self.assertEqual(len(metrics), 2)
            self.assertEqual([row["metrics"]["seed"] for row in records], [42, 43])
            self.assertNotEqual(records[0]["metrics"]["run_id"], records[1]["metrics"]["run_id"])
            self.assertEqual(set(config["prompts"]), {"research", "audit", "plan", "execute"})
            self.assertIn("calculate_total", config["tool_schemas"])

    def test_invalid_tasks_never_reach_the_model(self):
        with patch.object(FixtureClient, "preflight") as preflight:
            with self.assertRaises(ValueError):
                run_experiment(ExperimentSettings(), [task_for(0), task_for(0)],
                               client=FixtureClient())
            preflight.assert_not_called()

    def test_cli_rejects_invalid_configuration_before_launch(self):
        with patch("agent_system.cli.run_experiment") as run:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exit_result:
                    main(["--tasks", "7"])
            self.assertEqual(exit_result.exception.code, 2)
            run.assert_not_called()

    def test_package_runs_without_the_legacy_simulator_or_entry_file(self):
        package = Path(__file__).resolve().parents[1] / "agent_system"
        with tempfile.TemporaryDirectory(prefix="cse291-package-") as directory:
            shutil.copytree(package, Path(directory) / "agent_system",
                            ignore=shutil.ignore_patterns("__pycache__"))
            env = {**os.environ, "PYTHONPATH": ""}
            code = ('import sys; sys.modules["phase1"] = None; '
                    'from agent_system.cli import main; main(["--help"])')
            completed = subprocess.run([sys.executable, "-c", code], cwd=directory,
                                       env=env, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("python -m agent_system", completed.stdout)
