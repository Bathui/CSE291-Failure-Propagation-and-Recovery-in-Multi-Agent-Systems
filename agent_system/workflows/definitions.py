"""Declared dependency graph for the inventory workflow."""

DEPENDENCIES = {'research': ['request'],
 'audit': ['request'],
 'plan': ['research', 'request'],
 'execute': ['plan', 'audit']}

STAGES = ('research', 'audit', 'plan', 'execute')
