"""Composition root for the inventory experiment's roles, tools and evaluator."""
from agent_system.agents.auditor import DEFINITION as AUDITOR
from agent_system.agents.executor import DEFINITION as EXECUTOR
from agent_system.agents.planner import DEFINITION as PLANNER
from agent_system.agents.researcher import DEFINITION as RESEARCHER
from agent_system.agents.runtime import AgentRunner
from agent_system.domain.catalog import CATALOG
from agent_system.domain.tasks import validate_task
from agent_system.evaluation.inventory import evaluate_inventory_run
from agent_system.tools.authorization import TOOLS as AUTHORIZATION_TOOLS
from agent_system.tools.execution import TOOLS as EXECUTION_TOOLS
from agent_system.tools.inventory import build_inventory_tools
from agent_system.tools.planning import TOOLS as PLANNING_TOOLS
from agent_system.tools.registry import ToolRegistry
from agent_system.workflows.definitions import DEPENDENCIES, STAGES
from agent_system.workflows.runner import Workflow


AGENTS = {agent.name: agent for agent in (RESEARCHER, AUDITOR, PLANNER, EXECUTOR)}


def build_inventory_registry():
    return ToolRegistry((*build_inventory_tools(CATALOG), *AUTHORIZATION_TOOLS,
                         *PLANNING_TOOLS, *EXECUTION_TOOLS))


def build_inventory_workflow(client, max_turns=6):
    runner = AgentRunner(client, build_inventory_registry(), max_turns)
    return Workflow(runner, AGENTS, STAGES, DEPENDENCIES,
                    validate_task, evaluate_inventory_run)
