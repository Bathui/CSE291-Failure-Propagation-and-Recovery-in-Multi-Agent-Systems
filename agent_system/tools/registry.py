"""Tool lookup and argument validation, independent of roles and workflow order."""
from agent_system.protocol import validate_arguments


class ToolRegistry:
    def __init__(self, definitions):
        self._definitions = {}
        for definition in definitions:
            if definition.name in self._definitions:
                raise ValueError("Duplicate tool: " + definition.name)
            self._definitions[definition.name] = definition

    def get(self, name):
        if name not in self._definitions:
            raise ValueError("Unknown tool: " + str(name))
        return self._definitions[name]

    def definitions_for(self, names):
        return [self.get(name).as_api() for name in names]

    def schemas(self):
        return {name: definition.parameters for name, definition in self._definitions.items()}

    def call(self, name, arguments, context):
        definition = self.get(name)
        validate_arguments(arguments, definition.parameters)
        return definition.handler(arguments, context)
