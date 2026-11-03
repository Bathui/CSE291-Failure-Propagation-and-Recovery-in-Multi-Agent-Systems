# DataHub operation

The GPU profile provides a 24 GB MIG slice and 16 GB host memory. The prepared
environment lives under `~/private/cse291`, outside the repository:

- `src/llama.cpp`: CUDA-enabled llama.cpp build.
- `models/Qwen3-8B-Q4_K_M.gguf`: model weights.
- `.venv`: Python environment; the integration uses only the standard library.
- `src/experiment`: this repository's remote working copy.
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

Keep that foreground process running, then use a second terminal for experiments.
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

## Synchronize and run the four roles

When changes have been committed and pushed from your development machine:

```bash
cd ~/private/cse291/src/experiment
git pull --ff-only
~/private/cse291/.venv/bin/python -m agent_system --tasks 6 --output ~/private/cse291/results_llm
```

An explicitly uploaded working copy can also be used before publishing a commit.
Do not confuse that temporary copy with the repository's pushed version.
The initial integration was uploaded this way. Before the first Git pull that
introduces the same new files, reconcile or back up the uploaded files; Git can
otherwise refuse to overwrite untracked files. Check `git status` first.

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

This integration does not yet implement real-model fault injection or recovery.
`phase1.py` remains the separate deterministic simulator and its old outputs are
not evidence of real-model behavior.

See [live integration validation](integration-validation.md) for measured results.
