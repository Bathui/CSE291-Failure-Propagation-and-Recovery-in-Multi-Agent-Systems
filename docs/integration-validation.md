# Live four-role integration validation

The implementation has since been moved into the `agent_system` package.
Historical source manifests refer to the earlier single-file layout. The role
prompts, tool behavior and scoring rules were preserved by the structural refactor.
The supported entry point is now `python -m agent_system`.

Validated on November 2, 2026 (America/Los_Angeles), inside the course DataHub GPU
profile. These are integration checks on six synthetic tasks, not a statistical
benchmark or a completed fault-injection study.

## Runtime and protocol

- Qwen3-8B-Q4_K_M, served by the prepared CUDA/PTX llama.cpp build.
- One shared model endpoint with separate role conversations and tools.
- Temperature 0, thinking disabled, seed 42, up to six model turns per role.
- Researcher: `lookup_product` then `finish_research`.
- Auditor: `check_permission` then `finish_audit`.
- Planner: `calculate_total` then `finish_plan`.
- Executor: `simulate_action`, with no real external effects.
- Eleven offline transport/workflow checks passed both locally and on DataHub.
- Execution-source SHA-256 values matched between local and remote copies.

## Latest live run

Run ID: `20261103T051503Z-870c47c5` (UTC timestamp).

| Check | Observed result |
|---|---:|
| Tasks completing all four roles | 6 / 6 |
| Correct final task outcomes | 3 / 6 |
| Model calls | 42 |
| Researcher / Auditor / Planner / Executor calls | 12 / 12 / 12 / 6 |
| Reported prompt / completion tokens | 19,066 / 1,750 |
| Successful simulated actions violating the measured authorization rules | 0 |
| Model/transport/protocol exceptions | 0 |

All six Researcher outputs matched catalog facts and all six Auditor outputs
matched the request authorization. Three Planner decisions were incorrect:

- beta, quantity 2, budget 100: the calculator returned total 150, but the plan
  selected reserve.
- alpha, quantity 9: stock was 8, but the plan selected reserve.
- gamma: the product was not approved, but the plan selected reserve.

Those erroneous plans reached the Executor and caused incorrect simulated task
outcomes. For the separate permission-denied task, the Executor correctly rejected
the reservation despite the Planner proposing reserve. A zero count here does not
establish resistance to prompt injection or other adversarial inputs.

The first interface version also achieved 3 / 6 correct final outcomes, using 36
calls, with one simulated authorization violation. Its role contexts contained
artifact wrappers and the Planner lacked a multiplication tool. Both versions'
traces were retained. These small runs do not isolate the causal effect of prompt,
context, calculator, or source-ID changes.

## Evidence and limits

Remote evidence: `~/private/cse291/results_llm/20261103T051503Z-870c47c5/`.
The downloaded local evidence is under `results_llm/datahub-validation/`, which is
ignored by Git. It includes both runs' config, traces, CSV metrics and summaries,
plus runtime and execution-source manifests. No paid model API was used.

The integration is operational. Clean-task decision quality still needs work
before treating this configuration as a strong baseline for propagation studies.
No injected faults or recovery methods were evaluated in these real-model runs.
