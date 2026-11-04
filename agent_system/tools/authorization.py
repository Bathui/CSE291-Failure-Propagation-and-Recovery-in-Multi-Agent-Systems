"""Request authorization lookup and audit submission."""
import copy

from agent_system.protocol import BOOL, TEXT, object_schema
from agent_system.tools.base import ToolDefinition


def check_permission(args, context):
    source = context.stage_id + ":policy"
    result = {"allowed": context.task["authorized_action"] == "reserve",
              "destination": "internal_inventory", "source_id": source}
    context.evidence[source] = result
    return result, False


def finish_audit(args, context):
    if args["source_id"] not in context.evidence:
        raise ValueError("Read the role's lookup tool and use its source_id first")
    return copy.deepcopy(args), True


TOOLS = (
    ToolDefinition('check_permission', 'Read the authorization policy for this request.',
        object_schema({}), check_permission),
    ToolDefinition('finish_audit', 'Submit an audit and the source_id from check_permission.',
        object_schema({"allowed": BOOL, "destination": TEXT, "source_id": TEXT}), finish_audit),
)
