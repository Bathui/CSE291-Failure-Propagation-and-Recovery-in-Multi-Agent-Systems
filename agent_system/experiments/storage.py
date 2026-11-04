"""Experiment persistence and summary aggregation, without model or tool logic."""
import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ResultWriter:
    def __init__(self, output_root):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        self.path = Path(output_root) / stamp
        self.path.mkdir(parents=True, exist_ok=False)
        self.metrics = []
        self._trace_file = None

    def __enter__(self):
        self._trace_file = (self.path / "traces.jsonl").open("w", encoding="utf-8")
        return self

    def __exit__(self, *args):
        self._trace_file.close()

    def write_config(self, config):
        (self.path / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    def write_record(self, record):
        self._trace_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._trace_file.flush()
        self.metrics.append(record["metrics"])

    def finish(self):
        with (self.path / "runs.csv").open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=list(self.metrics[0]))
            writer.writeheader()
            writer.writerows(self.metrics)
        summary = {"runs": len(self.metrics), "successes": sum(row["success"] for row in self.metrics),
                   "success_rate": sum(row["success"] for row in self.metrics) / len(self.metrics),
                   "unauthorized_actions": sum(row["unauthorized_actions"] for row in self.metrics),
                   "model_calls": sum(row["model_calls"] for row in self.metrics)}
        (self.path / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
