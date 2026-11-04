# DataHub Inference and Local Experiment Manual

DataHub runs Qwen3-8B inference through llama.cpp. Your Windows machine runs the four-role workflow, tools, evaluation, and result storage.

```text
Local Python → local 127.0.0.1:18000 → SSH → dsmlp-login:18000
           → kubectl port-forward → DataHub container 127.0.0.1:8000 → llama.cpp
```

## 1. Start the DataHub GPU environment

Sign in to [UCSD DataHub](https://datahub.ucsd.edu) and select the course GPU profile `CSE291A_FA26_003 - Yiying Zhang [FA26]`. Open a JupyterLab Terminal and verify that the approximately 24 GB GPU slice is visible.

```bash
nvidia-smi
```

## 2. Install llama.cpp and model weights

Skip to step 3 if the server binary, weights, and startup script already exist under `~/private/cse291`. Otherwise, check the tools and disk space in DataHub.

```bash
command -v git cmake nvcc g++ curl
nvcc --version
df -h ~/private
mkdir -p ~/private/cse291/{src,models,logs}
```

Build the recorded llama.cpp revision in DataHub. These CUDA flags are for the course image with CUDA 12.0 and a Blackwell GPU. [llama.cpp build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)

```bash
cd ~/private/cse291
git clone https://github.com/ggml-org/llama.cpp.git src/llama.cpp
git -C src/llama.cpp checkout 2cbca389f515df455412dafa07e2b1359cc72a6d

cmake -S src/llama.cpp -B src/llama.cpp/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=80-virtual \
  '-DCMAKE_BUILD_RPATH=/opt/conda/lib;$ORIGIN' \
  -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link,/opt/conda/lib
cmake --build src/llama.cpp/build --target llama-server --parallel 4
```

Download and verify the [official Qwen GGUF weights](https://huggingface.co/Qwen/Qwen3-8B-GGUF).

```bash
cd ~/private/cse291
curl -fL --retry 3 -C - -o models/Qwen3-8B-Q4_K_M.gguf.part \
  https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/7c41481/Qwen3-8B-Q4_K_M.gguf
printf '%s  %s\n' \
  d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785 \
  models/Qwen3-8B-Q4_K_M.gguf.part | sha256sum -c - &&
mv -- models/Qwen3-8B-Q4_K_M.gguf.part models/Qwen3-8B-Q4_K_M.gguf
```

Save the following as `~/private/cse291/start_model.sh` if it does not already exist.

```bash
#!/usr/bin/env bash
set -eu
cd "$HOME/private/cse291"
export LD_LIBRARY_PATH="/opt/conda/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec ./src/llama.cpp/build/bin/llama-server \
  --model ./models/Qwen3-8B-Q4_K_M.gguf \
  --alias cse291-qwen3-8b \
  --host 127.0.0.1 --port 8000 \
  --n-gpu-layers 99 --ctx-size 8192 --parallel 1 \
  --jinja --reasoning off
```

## 3. Start and verify the model

In DataHub, check for `cse291-qwen3-8b` in the model list.

```bash
curl -fsS --max-time 10 http://127.0.0.1:8000/v1/models
```

If the connection is refused, start the service and leave its terminal open. Once the model loads, repeat the check in a second DataHub terminal. Warm up the model before measuring latency.

```bash
bash ~/private/cse291/start_model.sh
```

## 4. Forward the model port

Open a local PowerShell and sign in using your UCSD username. Complete password and Duo authentication as prompted. The examples use `Peter025`. [UCSD DSMLP guide](https://support.ucsd.edu/services?id=kb_article_view&sysparm_article=KB0032269)

```powershell
ssh Peter025@dsmlp-login.ucsd.edu
```

In the SSH shell on `dsmlp-login`, confirm your pod name and forward port 8000. Leave this terminal open after the forwarding message appears. [Kubernetes port forwarding guide](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)

```bash
kubectl get pods
kubectl port-forward --address 127.0.0.1 pod/dsmlp-jupyter-Peter025 18000:8000
```

In a second local PowerShell, open the SSH tunnel and leave it running. A quiet foreground session after authentication is expected.

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 127.0.0.1:18000:127.0.0.1:18000 Peter025@dsmlp-login.ucsd.edu
```

In a third local PowerShell, use `curl.exe` to verify that the tunnel returns `cse291-qwen3-8b`.

```powershell
curl.exe --fail --max-time 10 http://127.0.0.1:18000/v1/models
```

## 5. Run experiments locally

In the third PowerShell, change to the local repository root containing `agent_system/`. Run a single task using your local Python installation.

```powershell
python --version
python -m agent_system --base-url http://127.0.0.1:18000/v1 --tasks 1 --output results_llm
```

The first end-to-end check produced the following output.

```text
task=0 repeat=0 success=True stages=4 calls=7 error=None
```

`stages=4` and `error=None` indicate that all four stages completed without a runtime error. `success=True` means the task passed evaluation. To run all six built-in tasks three times each, use the following command.

```powershell
python -m agent_system --base-url http://127.0.0.1:18000/v1 --tasks 6 --repeats 3 --output results_llm
```

Each run writes a timestamped folder under local `results_llm/`. It contains `config.json`, `traces.jsonl`, `runs.csv`, and `summary.json`. The default is a clean live-model baseline with simulated tool effects.

## 6. Run the Phase 1 matrix

See [Phase 1 experiment results](phase1-results.md) for the measured comparison.

```powershell
python -m agent_system --base-url http://127.0.0.1:18000/v1 --suite --tasks 6 --repeats 3 --output results_llm
```

The suite compares the same tasks and seeds across 15 conditions. For a quick
check, use `--tasks 3 --repeats 1`. To run a single condition, replace
`--suite` with a fault such as `--fault stale-stock` and a policy such as
`--recovery restart`.

- **Faults.** Wrong price, stale stock, and timeout are accidental conditions.
  Malicious instruction is adversarial. The timeout simulates failure to
  deliver the completed Researcher artifact, without sleeping or inducing a
  real network timeout. Faults apply once, on the first attempt.
- **No recovery.** Record the first attempt as it ends.
- **Full restart.** Check intermediates after the first attempt, or restart
  immediately after a reported stage error. On detection, run the whole
  workflow once more with fresh state and no injected fault. The first attempt
  may already have taken a simulated action.
- **Always verify.** Independently check Researcher, Auditor, and Planner
  outputs before downstream use. Stop at the first mismatch and restart once
  without the injected fault. The verifier uses the trusted local catalog and
  policy. It adds checks and wall time, and uses zero model calls.

Both recovery policies also check the Executor's recorded action, SKU,
quantity, and destination against the plan and audit. An execution mismatch
triggers the same one-retry limit. If the mismatch persists on retry, the run
fails at the Executor stage. The trace retains all simulated actions.

Open `comparison.json` in the suite directory. Its pairs use the clean,
no-recovery run with the same task ID and seed as the reference. Direct
consumers received the injected artifact. Changed calculations and artifacts
show observed differences. A missing stage shows that work stopped before an
artifact was produced. Compare the first and final actions, success, discarded
calls and stages, verifier time, tokens, and end-to-end latency. Analyze
accidental and adversarial conditions separately. Final success describes the
retained attempt. Unauthorized actions count across all attempts, including
discarded ones. A later simulated success does not undo an earlier action.

## 7. Troubleshoot and shut down

| Symptom | What to check |
| --- | --- |
| SSH stops at `password:` or reports `Permission denied` | Enter your UCSD password and press Enter. Password input is hidden. Follow the Duo prompt. |
| DataHub port 8000 refuses the connection | Start the model and check its startup log. |
| llama.cpp cannot bind the HTTP socket | Query the model list in DataHub. Reuse the service if it already lists the expected model. |
| The local request returns an empty reply or times out | Check the model endpoint inside DataHub on port 8000, then on dsmlp-login at `127.0.0.1:18000/v1/models`, then on your computer at the same URL. Inspect the logs where the connection first fails. |
| The pod restarts or SSH disconnects | Confirm the pod name, verify the model service, and restart both forwarding sessions. |

Press Ctrl+C in each forwarding terminal when finished. To stop a foreground llama.cpp server, press Ctrl+C in its DataHub terminal.

Keep `src/llama.cpp`, `models/`, and `start_model.sh` on DataHub. Once the local workflow passes its end-to-end check, the old remote checkout at `~/private/cse291/src/experiment` can be removed. Earlier remote results are stored separately under `~/private/cse291/results_llm/`.
