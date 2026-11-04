"""Bounded model/tool loop shared by role definitions."""
import copy
import json
import time

from agent_system.clients.base import ChatModel
from agent_system.protocol import AgentError, strict_json
from agent_system.tools.base import ToolContext
from agent_system.tools.registry import ToolRegistry


class AgentRunner:
    def __init__(self, client: ChatModel, tools: ToolRegistry, max_turns=6):
        self.client = client
        self.tools = tools
        self.max_turns = max_turns

    def run(self, definition, task, inputs, seed, events, stage_id):
        role = definition.name
        visible = ({"request": task} if definition.include_request else {})
        # Keep provenance in the trace; expose the actual parent values without wrappers.
        visible.update({name: copy.deepcopy(artifact["value"]) for name, artifact in inputs.items()})
        messages = [{"role": "system", "content": definition.prompt},
                    {"role": "user", "content": json.dumps(visible, ensure_ascii=False)}]
        tools = self.tools.definitions_for(definition.tool_names)
        context = ToolContext(task, stage_id, inputs=visible)
        for turn in range(self.max_turns):
            start = time.perf_counter()
            call_event = {"event": "model_call", "stage": role, "stage_id": stage_id,
                          "turn": turn, "seed": seed,
                          "messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)}
            events.append(call_event)
            try:
                response = self.client.chat(messages, tools, seed)
                call_event["response"] = response
                call_event["usage"] = response.get("usage") if isinstance(response, dict) else None
                message = response["choices"][0]["message"]
                if not isinstance(message, dict) or message.get("role") != "assistant":
                    raise ValueError("Expected an assistant message")
                if response["choices"][0].get("finish_reason") == "length":
                    raise ValueError("Model output truncated; increase --max-tokens")
            except Exception as exc:
                call_event["error"] = str(exc)
                raise AgentError("%s model/protocol failure: %s" % (role, exc)) from exc
            finally:
                call_event["duration_ms"] = (time.perf_counter() - start) * 1000
            messages.append(message)
            calls = message.get("tool_calls")
            if not calls:
                messages.append({"role": "user", "content":
                                 "Complete your role using the provided tools. Plain text is not a submission."})
                continue
            if not isinstance(calls, list):
                raise AgentError("tool_calls must be an array")
            finished = None
            call_ids = set()
            for call in calls:
                if not isinstance(call, dict) or not isinstance(call.get("id"), str) or not call["id"]:
                    raise AgentError("Tool call is missing its id")
                if call["id"] in call_ids:
                    raise AgentError("Duplicate tool call id")
                call_ids.add(call["id"])
                function = call.get("function", {})
                name = function.get("name") if isinstance(function, dict) else None
                event = {"event": "tool_call", "stage": role, "stage_id": stage_id,
                         "tool_call_id": call["id"], "name": name,
                         "raw_arguments": function.get("arguments") if isinstance(function, dict) else None}
                events.append(event)
                try:
                    if finished is not None:
                        raise ValueError("Role already submitted; extra call was not executed")
                    if name not in definition.tool_names:
                        raise ValueError("Tool is not available to this role")
                    arguments = strict_json(function["arguments"])
                    event["arguments"] = arguments
                    result, is_final = self.tools.call(name, arguments, context)
                    event.update({"status": "ok", "result": copy.deepcopy(result)})
                    if is_final:
                        finished = result
                except (ValueError, KeyError, TypeError) as exc:
                    result = {"error": str(exc)}
                    event.update({"status": "error", "result": result})
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, ensure_ascii=False)})
            if finished is not None:
                return finished
        raise AgentError("%s exceeded %s model turns" % (role, self.max_turns))

