# DataHub operation

The GPU profile provides a 24 GB MIG slice and 16 GB host memory. The prepared
environment lives under `~/private/cse291`, outside the repository:

- `src/llama.cpp`: CUDA-enabled llama.cpp build.
- `models/Qwen3-8B-Q4_K_M.gguf`: model weights.
- `.venv`: Python environment; the integration uses only the standard library.
- `start_model.sh`, `stop_model.py`, `smoke_test.py`: model lifecycle and diagnostics.
- `logs`: server output, setup manifest, model SHA-256 and protocol smoke results.

## Start and check the model

The initial setup may already have a model running. Test before starting a second
server on the same port:

```bash
~/private/cse291/.venv/bin/python ~/private/cse291/smoke_test.py
```

After a DataHub restart, open a terminal and start the model:

```bash
bash ~/private/cse291/start_model.sh
```

Keep that foreground process running while the local workflow uses the model.
Stop a foreground server with Ctrl+C. To stop the background server created by
the initial setup, use:

```bash
~/private/cse291/.venv/bin/python ~/private/cse291/stop_model.py
```

The server binds only to `127.0.0.1:8000` inside DataHub. Python sends requests to
`http://127.0.0.1:8000/v1` and uses the alias `cse291-qwen3-8b`. No public model
endpoint or paid model API is needed.

The school image's CUDA 12.0 compiler requires a PTX-compatible build for this
Blackwell device. The prepared build uses `CMAKE_CUDA_ARCHITECTURES=80-virtual`
and includes `/opt/conda/lib` in its runtime library search path. The initial
inference can include driver JIT work; warm up before comparing execution times.
This is a working compatibility configuration, not an optimized native build.
Record `logs/setup-manifest.json` alongside experiment results when reporting
model, quantization and runtime versions.

## Run the four roles locally

Follow the [manual](manual.md) to forward the model port through SSH and run
the local checkout. DataHub serves inference and the local process runs the
workflow, tools, fault injection, verification, and result storage.

The four roles share model weights but not their conversations. Data flow is:

```text
request -> research -> plan -> execute
request -> audit ------------> execute
request -------------> plan
```

The role prompts and capabilities live in `agent_system/agents/`; the model
adapter lives in `clients/`, tools in `tools/`, orchestration in `workflows/`,
offline scoring in `evaluation/`, and experiment output in `experiments/`.
`scenarios/inventory.py` assembles these components. The package entry point is
`python -m agent_system`; the earlier `phase1_llm.py` entry has been removed.

Each run has isolated simulated effects. Evaluation uses the trusted catalog
outside model contexts. Failed or unauthorized simulated actions remain visible
in traces and cannot be replaced by a synthetic successful result.

The local `--suite` entry point pairs each injected run with a clean reference
and compares the no-recovery, full-restart, and always-verify policies.
`phase1.py` is a separate deterministic simulator.

See [Phase 1 experiment results](phase1-results.md) for the paired live-model results.
