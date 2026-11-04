"""HTTP transport for the prepared llama.cpp server."""
import json
import urllib.error
import urllib.parse
import urllib.request

from agent_system.protocol import AgentError, strict_json


class LlamaCppClient:
    def __init__(self, base_url="http://127.0.0.1:8000/v1",
                 model="cse291-qwen3-8b", timeout=180, max_tokens=512):
        self.base_url = base_url.rstrip("/")
        if urllib.parse.urlparse(self.base_url).scheme not in ("http", "https"):
            raise ValueError("base_url must be HTTP or HTTPS")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def request(self, path, payload=None):
        request = urllib.request.Request(
            self.base_url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return strict_json(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise AgentError("HTTP %s: %s" % (exc.code, detail)) from exc
        except (OSError, ValueError) as exc:
            raise AgentError("Model request failed: " + str(exc)) from exc

    def preflight(self):
        models = self.request("/models")
        if not isinstance(models, dict) or not isinstance(models.get("data"), list):
            raise AgentError("Invalid /models response")
        ids = [entry.get("id") for entry in models["data"] if isinstance(entry, dict)]
        if self.model not in ids:
            raise AgentError("Model alias %r not available; server lists %r" % (self.model, ids))
        return models

    def chat(self, messages, tools, seed):
        return self.request("/chat/completions", {
            "model": self.model, "messages": messages, "tools": tools,
            "tool_choice": "auto", "parallel_tool_calls": False,
            "temperature": 0, "seed": seed, "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}})

