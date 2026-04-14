"""
Node Specification - defines the capabilities and behavior of test nodes

This module defines NodeSpec which describes what a node can do, what inputs
it accepts, what outputs it produces, and potential failure modes. This is
the information that agents use for planning and decision-making.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParameterSpec:
    """
    Parameter specification for a node

    Attributes:
        name: Parameter name
        type: Parameter type (string, number, boolean, object, array)
        description: Description of the parameter
        required: Whether this parameter is required
        default: Default value (if optional)
        options: List of allowed values (for enum types)
    """
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    options: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            data["default"] = self.default
        if self.options:
            data["options"] = self.options
        return data


@dataclass
class OutputSpec:
    """
    Output specification for a node

    Attributes:
        name: Output name
        type: Output type
        description: Description of the output
        example: Example value (for documentation)
    """
    name: str
    type: str
    description: str
    example: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
        }
        if self.example is not None:
            data["example"] = self.example
        return data


@dataclass
class NodeSpec:
    """
    Node Specification - defines the capabilities and behavior of a test node

    Attributes:
        node_type: Node type identifier (must be unique)
        name: Human-readable name
        description: Detailed description of what this node does
        goals: List of goals this node can achieve (used by agents for planning)
        inputs: List of input parameters
        outputs: List of outputs
        failure_modes: List of potential failure modes and how to handle them
        category: Node category (UI, API, Data, Validation, Report, Control)
        icon: Icon for UI display
        tags: Tags for classification
    """
    node_type: str
    name: str
    description: str
    goals: List[str] = field(default_factory=list)
    inputs: List[ParameterSpec] = field(default_factory=list)
    outputs: List[OutputSpec] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    category: str = "general"
    icon: str = "🤖"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "node_type": self.node_type,
            "name": self.name,
            "description": self.description,
            "goals": self.goals,
            "inputs": [param.to_dict() for param in self.inputs],
            "outputs": [output.to_dict() for output in self.outputs],
            "failure_modes": self.failure_modes,
            "category": self.category,
            "icon": self.icon,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeSpec':
        """Create from dictionary representation"""
        inputs = []
        for param_data in data.get("inputs", []):
            inputs.append(ParameterSpec(**param_data))

        outputs = []
        for output_data in data.get("outputs", []):
            outputs.append(OutputSpec(**output_data))

        return cls(
            node_type=data["node_type"],
            name=data["name"],
            description=data["description"],
            goals=data.get("goals", []),
            inputs=inputs,
            outputs=outputs,
            failure_modes=data.get("failure_modes", []),
            category=data.get("category", "general"),
            icon=data.get("icon", "🤖"),
            tags=data.get("tags", [])
        )

    def get_parameter(self, name: str) -> Optional[ParameterSpec]:
        """Get a parameter specification by name"""
        for param in self.inputs:
            if param.name == name:
                return param
        return None

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Validate parameters against the specification

        Args:
            parameters: Parameters to validate

        Returns:
            List of error messages (empty if validation passes)
        """
        errors = []

        for param in self.inputs:
            if param.required and param.name not in parameters:
                errors.append(f"Missing required parameter: {param.name}")
            elif param.name in parameters:
                value = parameters[param.name]
                error = self._validate_parameter_type(param, value)
                if error:
                    errors.append(error)

                if param.options and value not in param.options:
                    errors.append(
                        f"Parameter '{param.name}' must be one of: {', '.join(str(opt) for opt in param.options)}"
                    )

        return errors

    def _validate_parameter_type(self, param: ParameterSpec, value: Any) -> Optional[str]:
        """
        Validate a single parameter value against its type specification

        Args:
            param: Parameter specification
            value: Value to validate

        Returns:
            Error message if validation fails, None otherwise
        """
        param_type = param.type

        if param_type == "string":
            if not isinstance(value, str):
                return f"Parameter '{param.name}' must be a string"
        elif param_type == "number":
            if not isinstance(value, (int, float)):
                return f"Parameter '{param.name}' must be a number"
        elif param_type == "integer":
            if not isinstance(value, int):
                return f"Parameter '{param.name}' must be an integer"
        elif param_type == "boolean":
            if not isinstance(value, bool):
                return f"Parameter '{param.name}' must be a boolean"
        elif param_type == "array":
            if not isinstance(value, list):
                return f"Parameter '{param.name}' must be an array"
        elif param_type == "object":
            if not isinstance(value, dict):
                return f"Parameter '{param.name}' must be an object"

        return None

    def to_json_schema(self) -> Dict[str, Any]:
        """
        Convert NodeSpec to JSON Schema format

        Returns:
            JSON Schema compatible dictionary
        """
        properties = {}
        required = []

        for param in self.inputs:
            type_mapping = {
                "string": "string",
                "number": "number",
                "integer": "integer",
                "boolean": "boolean",
                "array": "array",
                "object": "object"
            }

            schema_type = type_mapping.get(param.type, "string")

            prop_schema = {
                "type": schema_type,
                "description": param.description
            }

            if param.default is not None:
                prop_schema["default"] = param.default

            if param.options:
                prop_schema["enum"] = param.options

            properties[param.name] = prop_schema

            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


# Default Node Specifications
DEFAULT_NODE_SPECS = [
    NodeSpec(
        node_type="ui_test",
        name="UI Test",
        description="Performs UI testing using Playwright",
        goals=["Test UI functionality", "Verify user interactions", "Check page elements"],
        inputs=[
            ParameterSpec(
                name="url",
                type="string",
                description="URL of the page to test",
                required=False
            ),
            ParameterSpec(
                name="browser",
                type="string",
                description="Browser type (chromium, firefox, webkit)",
                required=False,
                default="chromium"
            ),
            ParameterSpec(
                name="headless",
                type="boolean",
                description="Run browser in headless mode",
                required=False,
                default=True
            ),
            ParameterSpec(
                name="timeout",
                type="integer",
                description="Timeout in milliseconds",
                required=False,
                default=30000
            ),
            ParameterSpec(
                name="viewport",
                type="object",
                description="Browser viewport settings",
                required=False,
                default={"width": 1280, "height": 720}
            )
        ],
        outputs=[
            OutputSpec(
                name="screenshot",
                type="string",
                description="Base64 encoded screenshot of the page",
                example="data:image/png;base64,..."
            ),
            OutputSpec(
                name="page_source",
                type="string",
                description="HTML source of the page",
                example="<html>...</html>"
            )
        ],
        failure_modes=[
            "Page not found",
            "Element not accessible",
            "Timeout waiting for element",
            "Network error"
        ],
        category="ui",
        icon="🖥️"
    ),
    NodeSpec(
        node_type="api_test",
        name="API Test",
        description="Sends an HTTP request and validates the response",
        goals=["Test API endpoints", "Validate API responses", "Check API performance"],
        inputs=[
            ParameterSpec(
                name="url",
                type="string",
                description="API endpoint URL",
                required=True
            ),
            ParameterSpec(
                name="method",
                type="string",
                description="HTTP method",
                required=True,
                default="GET",
                options=["GET", "POST", "PUT", "DELETE", "PATCH"]
            ),
            ParameterSpec(
                name="headers",
                type="object",
                description="HTTP headers",
                required=False,
                default={}
            ),
            ParameterSpec(
                name="body",
                type="object",
                description="Request body",
                required=False,
                default={}
            ),
            ParameterSpec(
                name="expected_status",
                type="number",
                description="Expected HTTP status code",
                required=False,
                default=200
            )
        ],
        outputs=[
            OutputSpec(
                name="status_code",
                type="number",
                description="HTTP status code",
                example=200
            ),
            OutputSpec(
                name="response_time",
                type="number",
                description="Response time in milliseconds",
                example=150
            ),
            OutputSpec(
                name="response",
                type="object",
                description="Response body",
                example={"data": "..."}
            )
        ],
        failure_modes=[
            "Connection timeout",
            "Invalid status code",
            "Response validation failed",
            "Network error"
        ],
        category="api",
        icon="🔌"
    ),
    NodeSpec(
        node_type="data_generation",
        name="Data Generation",
        description="Generates test data for testing purposes",
        goals=["Generate test data", "Create random data", "Mock API responses"],
        inputs=[
            ParameterSpec(
                name="data_type",
                type="string",
                description="Type of data to generate",
                required=True,
                options=["user", "product", "order", "address", "random"]
            ),
            ParameterSpec(
                name="count",
                type="number",
                description="Number of data items to generate",
                required=False,
                default=1
            )
        ],
        outputs=[
            OutputSpec(
                name="data",
                type="array",
                description="Generated data items",
                example=[{"name": "Test User", "email": "test@example.com"}]
            )
        ],
        failure_modes=[
            "Invalid data type",
            "Generation failed"
        ],
        category="data",
        icon="📊"
    ),
    NodeSpec(
        node_type="validation",
        name="Validation",
        description="Validates data against expectations",
        goals=["Validate API responses", "Check data quality", "Assert conditions"],
        inputs=[
            ParameterSpec(
                name="data",
                type="object",
                description="Data to validate",
                required=True
            ),
            ParameterSpec(
                name="expectations",
                type="object",
                description="Expected values and conditions",
                required=True
            )
        ],
        outputs=[
            OutputSpec(
                name="valid",
                type="boolean",
                description="Whether validation passed",
                example=True
            ),
            OutputSpec(
                name="errors",
                type="array",
                description="List of validation errors",
                example=["Field 'email' is invalid"]
            )
        ],
        failure_modes=[
            "Validation failed",
            "Invalid data format"
        ],
        category="validation",
        icon="✅"
    ),
    NodeSpec(
        node_type="report",
        name="Report Generation",
        description="Generates test reports",
        goals=["Generate test reports", "Export results", "Analyze data"],
        inputs=[
            ParameterSpec(
                name="data",
                type="object",
                description="Test data to include in report",
                required=True
            ),
            ParameterSpec(
                name="format",
                type="string",
                description="Report format",
                required=False,
                default="json",
                options=["json", "html", "markdown"]
            )
        ],
        outputs=[
            OutputSpec(
                name="report",
                type="string",
                description="Generated report",
                example="..."
            )
        ],
        failure_modes=[
            "Report generation failed",
            "Invalid data format"
        ],
        category="report",
        icon="📝"
    )
]


def register_default_node_specs():
    """
    将 DEFAULT_NODE_SPECS 注册到 global_node_registry。
    
    在应用启动时调用，确保默认节点类型可用于 FlowIR 执行。
    使用占位执行器类，实际执行逻辑由具体节点实现覆盖。
    """
    from core.flow.test_node_registry import global_node_registry

    class DefaultNodeExecutor:
        """默认节点执行器占位类"""
        def __init__(self, spec=None, **kwargs):
            self.spec = spec

        async def execute(self, context=None, **kwargs):
            raise NotImplementedError(
                f"Node type '{self.spec.node_type if self.spec else 'unknown'}' "
                "has no concrete executor registered. "
                "Register a specific executor to enable execution."
            )

    for spec in DEFAULT_NODE_SPECS:
        if not global_node_registry.validate_node_type(spec.node_type):
            global_node_registry.register(spec, DefaultNodeExecutor)
