"""Shared JSON validation and agent errors, independent of any scenario."""
import json
import math

class AgentError(RuntimeError):
    """A recorded model, protocol, or bounded-agent failure."""


def strict_json(text):
    def invalid(value):
        raise ValueError("Non-finite JSON value: " + value)
    return json.loads(text, parse_constant=invalid)


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string"}
BOOL = {"type": "boolean"}
NUMBER = {"type": "number", "minimum": 0}
INTEGER = {"type": "integer", "minimum": 0}
POSITIVE = {"type": "integer", "minimum": 1}

def validate_arguments(value, schema):
    """Validate the small JSON Schema subset used by this workflow."""
    if not isinstance(value, dict):
        raise ValueError("Arguments must be a JSON object")
    if set(value) != set(schema["required"]):
        raise ValueError("Expected exactly these fields: " + ", ".join(schema["required"]))
    for name, rule in schema["properties"].items():
        item = value[name]
        kind = rule["type"]
        valid = ((kind == "string" and isinstance(item, str))
                 or (kind == "boolean" and type(item) is bool)
                 or (kind == "integer" and type(item) is int)
                 or (kind == "number" and type(item) in (int, float)
                     and math.isfinite(item)))
        if not valid:
            raise ValueError("Invalid type for " + name)
        if "minimum" in rule and item < rule["minimum"]:
            raise ValueError("Value below minimum for " + name)

