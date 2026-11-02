
# Failure Propagation and Recovery in Multi-Agent Systems

CSE 291 - Phase 1

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
