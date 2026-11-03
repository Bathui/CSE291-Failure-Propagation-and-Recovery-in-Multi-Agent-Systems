
# Failure Propagation and Recovery in Multi-Agent Systems

CSE 291 - Phase 1

## Real LLM agents (DataHub)

The `agent_system` package connects all four roles to the shared llama.cpp model server.
Each role has its own context and permitted tools. Researcher and Auditor query
independent local tools; Planner uses a multiplication tool and submits a plan; Executor invokes a simulated
action tool. No model-generated code or real external action is executed.

Run **inside the GPU DataHub environment**, where the model server is running:

```bash
cd ~/private/cse291/src/experiment
~/private/cse291/.venv/bin/python -m agent_system --tasks 6 --output ~/private/cse291/results_llm
```

Defaults: base URL `http://127.0.0.1:8000/v1`, model alias `cse291-qwen3-8b`.
Override these with `--base-url`, `--model`, or `LLAMA_BASE_URL` / `LLAMA_MODEL`.
The localhost address refers to the machine running Python: opening that address
in a browser on your laptop does not access the DataHub model server.

Results are written to a new timestamped folder beneath `results_llm/`:
`config.json`, `traces.jsonl`, `runs.csv`, and `summary.json`. Traces include exact
role inputs, model responses, tool calls, artifact dependencies, timing and usage.
Protocol and connection failures are recorded; there is no simulator fallback.

The six built-in cases cover approval, budget, stock and authorization boundaries.
For a larger task set, pass `--task-file tasks.json` (a JSON array of objects with
`id`, `sku`, `quantity`, `budget`, and `authorized_action`). `--repeats` controls
repetition; seeds, prompts and schemas are saved with each run. Fixed seeds do not
guarantee deterministic GPU inference. Token counts are actual server usage,
not the synthetic cost units of the simulator.

This entry point currently validates role integration without injected faults or
recovery methods. The remaining sections describe the original simulator only.

Local protocol checks (no model server required):

```bash
python -m unittest discover -s tests -v
```

See [DataHub operation](docs/datahub.md) for model lifecycle and code synchronization.
The initial live integration results and current model limitations are recorded
in [integration validation](docs/integration-validation.md).

## Code organization

```text
agent_system/
  __main__.py, cli.py       # Package entry and command-line arguments
  clients/                 # Model interface and llama.cpp HTTP adapter
  agents/                  # Four role definitions and the bounded tool loop
  tools/                   # Inventory, authorization, planning and simulation tools
  domain/                  # Shared catalog, task fixtures and business rules
  scenarios/               # Composition of the inventory experiment
  workflows/               # Dependency graph and artifact orchestration
  evaluation/              # Offline scoring and usage metrics
  experiments/             # Runtime settings, experiment execution and file output
tests/                     # Workflow, transport and application checks
```

The workflow accepts its agent runner, role definitions, dependencies, validator
and evaluator as dependencies. Agent execution does not import the scoring
oracle or command-line interface. Both the live scenario and legacy simulator
read the catalog and graph from their shared owning modules; the live package
does not import `phase1.py`.

## Overview

This project investigates how incorrect or malicious
intermediate results propagate through multi-agent systems.

Phase 1 implements a deterministic multi-agent workflow,
controlled fault injection, dependency tracking, and
recovery baseline comparisons.

## Architecture

The system contains four simulated agents:

1. Researcher - Retrieves product information.
2. Auditor - Checks operation permissions.
3. Planner - Selects an action using research results.
4. Executor - Performs a simulated action.

Dependencies:

Request -> Researcher -> Planner -> Executor
Request -> Auditor -> Executor

## Fault Injection

Accidental faults:
- Wrong price
- Stale stock
- Timeout

Adversarial faults:
- Malicious instruction
- Audit corruption
- Planner tampering

## Baselines

1. No recovery
2. Full restart
3. Always verify intermediate results

Full restart assumes the faulty result is known.
Verification uses trusted ground truth.

## Evaluation Metrics

- Task success rate
- Unauthorized action rate
- Fault consumption
- Propagated stages
- Wasted work
- Recomputed stages
- Retained valid work
- Execution latency
- Synthetic inference cost

## Requirements

Python 3.9 or newer.

No external Python dependencies are required.

## Running Experiments

Run:

    python phase1.py --tasks 90 --output results

The program evaluates 90 tasks, seven fault conditions,
and three methods, producing 1,890 experiment records.

## Outputs

The results directory contains:

- runs.csv: Individual experiment metrics
- summary.csv: Aggregated results
- traces.jsonl: Complete execution traces
- config.json: Experiment configuration

## Reproducibility

Tasks and injected faults are deterministic.
Wall-clock latency may vary across machines.

The system uses simulated agents, not actual LLM inference.
Inference costs are synthetic weighted units.

All actions are simulated; no external service is modified.

## Phase 2

Phase 2 will implement dependency-aware selective recovery.

The recovery mechanism will invalidate faulty results,
identify affected downstream stages, preserve independent
valid outputs, and recompute only necessary operations.
