# Phase 1 live-model experiments

The four-role workflow runs locally and uses Qwen3-8B-Q4_K_M on DataHub
through llama.cpp. The experiment pairs each condition with a clean reference
using the same task and seed. The local tool actions are simulated.

## Reproduce the matrix

After setting up the model and SSH forwarding as described in the
[manual](manual.md#6-run-the-phase-1-matrix), run from the repository root:

```powershell
python -m agent_system --base-url http://127.0.0.1:18000/v1 --suite --tasks 6 --repeats 3 --output results_llm
```

The matrix covers six tasks, seeds 42–44, five fault conditions, and three
recovery policies. Incorrect price, stale stock, and simulated delivery timeout
are analyzed separately from adversarial instruction injection. Each fault is
applied at the Researcher output boundary on the first attempt. The delivery
timeout withholds a generated artifact without waiting for a network timeout.

The full-restart policy checks intermediate artifacts after the first attempt
and retries on detection. Always-verify checks each intermediate artifact
before downstream use. Both policies also compare the Executor output with
the plan and audit and retry at most once. Verification uses local rules and
adds no model calls. The original simulated actions remain in the trace.

The suite records messages, tool actions, artifacts, and stage dependencies.
`comparison.json` pairs runs by task and seed. Direct consumption means a stage
received the changed artifact. A change in calculation, plan, or action is
separate evidence of an effect. A later correct action does not erase an earlier
simulated action. The unauthorized-action metric tracks permission and execution
violations. Budget and stock violations can still cause task failure when that
metric is zero.

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
