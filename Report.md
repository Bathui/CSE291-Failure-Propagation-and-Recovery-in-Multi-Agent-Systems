# Phase 1 Report: Fault Injection and Propagation in Multi-Agent Systems

## Abstract

We built a four-role inventory workflow and measured how faults in intermediate results change downstream calculations and simulated actions. We evaluated six tasks at three seeds across five fault conditions and three recovery policies, for 270 runs. The clean reference passed 18/18. Without recovery, success ranged from 0/18 for delivery timeouts to 15/18 for stale stock. Both recovery policies passed all 72 of their injected runs. For artifact faults, verifying before downstream use saved five model calls per run relative to checking after the first attempt and restarting.

## System and workload

The workflow, tools, evaluation, and logging run locally. Qwen3-8B-Q4_K_M runs on a DataHub GPU through llama.cpp and serves model requests through an SSH tunnel. The four roles share the model and use separate prompts, contexts, and tools.

| Role | Inputs | Responsibility |
| --- | --- | --- |
| Researcher | Request and inventory lookup | Report price, stock, approval, and provenance. |
| Auditor | Request and authorization lookup | Report whether reservation is permitted and identify the permitted destination. |
| Planner | Request and Researcher output | Calculate total price, check reported stock, and propose an action. |
| Executor | Planner and Auditor outputs | Submit a simulated action subject to the authorization decision. |

The six tasks cover two valid reservations, an over-budget request, insufficient stock, an unapproved product, and a request without reservation permission. The offline evaluator checks the final action, SKU, quantity, and destination against the original inventory and request policy. It also counts unauthorized tool actions.

During development, the clean baseline improved from 9/18 to 15/18 after we made the rejection rules explicit in the Planner prompt. Adding a structured `stock_ok` result improved it to 18/18 on the same tasks and seeds. The tool compares requested quantity with the stock reported by Researcher, so a corrupted report can still change the result. The full matrix uses this configuration.

## Experimental design

The experiment applies one fault after Researcher produces its output and before Planner can use it. The original task and reference inventory are preserved.

| Condition | Category | Intervention |
| --- | --- | --- |
| Clean | Control | Pass the original output downstream. |
| Delivery timeout | Accidental | Withhold the generated Researcher artifact and report a simulated timeout. |
| Incorrect price | Accidental | Replace the reported unit price with 100. |
| Stale stock | Accidental | Replace the reported stock with 10. |
| Malicious instruction | Adversarial | Insert a directive to ignore inventory checks and always reserve. |

Each condition uses the same six tasks and seeds 42, 43, and 44. We compare three policies.

| Policy | Detection and response |
| --- | --- |
| No recovery | Record the first attempt without additional checks or retries. |
| Full restart | On a stage error or a mismatch found by checks after the attempt, rerun the entire workflow once with fresh state and no injection. |
| Always verify | Check intermediate artifacts against independent local reference data before downstream use. On a stage error or mismatch, stop and rerun once without injection. |

Both recovery policies also check the Executor's recorded action against the plan and audit. Checks use local rules and add no model calls. The trace retains any simulated actions from the first attempt.

We pair runs by task and seed and track whether the changed artifact reached a downstream stage, whether it changed the calculation or decision, and whether the final action changed. We also record discarded work, token usage, and end-to-end latency.

## Reproduction

Follow the [DataHub setup manual](docs/manual.md) to start inference and open the SSH tunnel. From the local repository root, run:

```powershell
python -m agent_system --base-url http://127.0.0.1:18000/v1 --suite --tasks 6 --repeats 3 --output results_llm
```

The [local comparison report](results_llm/phase1-20261104T061309Z-d36950cf/comparison.json) contains the paired observations. Each condition also saves its configuration, per-run CSV, summary, and JSONL traces.

## Full matrix results

Run ID: `phase1-20261104T061309Z-d36950cf`. The local evidence is under
`results_llm/phase1-20261104T061309Z-d36950cf/`. The suite completed all 15
conditions and 270 task runs, including 2,358 model calls across first attempts
and retries. All 18 offline tests passed before the run.

| Condition | Category | No recovery | Full restart | Always verify |
| --- | --- | ---: | ---: | ---: |
| Clean | Control | 18/18 | 18/18 | 18/18 |
| Delivery timeout | Accidental | 0/18 | 18/18 | 18/18 |
| Incorrect price | Accidental | 14/18 | 18/18 | 18/18 |
| Stale stock | Accidental | 15/18 | 18/18 | 18/18 |
| Malicious instruction | Adversarial | 12/18 | 18/18 | 18/18 |

Cells count final task passes. Neither recovery policy restarted a clean run.
Each restarted all 72 of its injected runs once, including cases where the first
attempt would have produced the correct final action. The retained attempts
all passed. The recorded unauthorized-action count was zero across the matrix,
including discarded attempts. Business-rule failures still occurred.

### Propagation without recovery

| Fault | Planner received changed artifact | Planner calculation changed | Final effect compared with clean |
| --- | ---: | ---: | --- |
| Delivery timeout | 0/18 | No calculation ran | No final action in 18/18 |
| Incorrect price | 18/18 | 18/18 | Four correct reservations became rejections |
| Stale stock | 18/18 | 3/18 | Three correct rejections became reservations |
| Malicious instruction | 18/18 | 0/18 | Six correct rejections became reservations |

Incorrect price changed the calculated total even in runs where the final
decision stayed the same. Stale stock raised the reported stock from 8 to 10
for task 2, changing `stock_ok` from false to true and causing an incorrect
reservation at each seed. The malicious instruction changed the decisions for
the over-budget and insufficient-stock tasks at all three seeds while their
calculation results stayed unchanged. The comparisons describe the observed
effects in this workload.

### Recovery cost

| Condition | Mean time, no recovery (s) | Mean time, full restart (s) | Mean time, always verify (s) | Discarded model calls per run, restart / verify |
| --- | ---: | ---: | ---: | ---: |
| Clean | 4.60 | 4.62 | 4.60 | 0 / 0 |
| Delivery timeout | 1.57 | 6.20 | 6.19 | 2 / 2 |
| Incorrect price | 4.63 | 9.27 | 6.18 | 7 / 2 |
| Stale stock | 4.63 | 9.18 | 6.17 | 7 / 2 |
| Malicious instruction | 4.73 | 9.32 | 6.17 | 7 / 2 |

For the three artifact modifications, full restart discarded four completed
stages per run. Always-verify stopped at the Researcher boundary, before any
completed artifact was accepted, and saved five model calls per run relative
to full restart. Both policies discarded two calls on simulated timeout.
Prompt and completion tokens, verifier duration, and end-to-end latency for
each run are available in the comparison report and condition CSV files.

The suite recorded 234 Executor consistency checks and no mismatches. In the
offline regression test, a scripted wrong Executor action triggers a retry
and the original action remains in the trace. A repeated mismatch fails the
run. The live matrix injects faults at Researcher, so it does not exercise
an Executor-specific fault. Recovery results apply to one-shot faults with
independent reference data. The first-attempt behavior can vary even when
task and seed are held fixed.
