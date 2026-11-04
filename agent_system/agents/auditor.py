"""Auditor role prompt and capabilities."""
from agent_system.agents.base import AgentDefinition


PROMPT = """You are the Auditor. Call check_permission, then finish_audit with
the policy's allowed flag, destination and source_id. Audit only the request and
policy, independently of the Researcher and Planner. Never invent a policy."""

DEFINITION = AgentDefinition(
    name='audit',
    prompt=PROMPT,
    tool_names=('check_permission', 'finish_audit'),
    include_request=True,
)
