"""
Test case generation tool from API specifications
"""

import json
from typing import Dict, Any, List, Optional
import logging
from faker import Faker

from core.tools.base_tool import BaseTool, ToolResult
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class TestCaseGeneratorTool(BaseTool):
    """Test case generation tool from API specifications"""
    
    def __init__(self):
        super().__init__(
            name="test_case_generator",
            description="Generate test cases from API specifications (OpenAPI/Swagger)",
            version="1.0.0"
        )
        self.faker = Faker()
        self.faker.seed_instance(42)  # Fixed seed for reproducibility
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        """Build parameters schema"""
        return {
            "api_spec": {
                "type": "object",
                "description": "API specification (OpenAPI/Swagger format)"
            },
            "base_url": {
                "type": "string",
                "description": "Base URL for API endpoints",
                "default": ""
            },
            "test_types": {
                "type": "array",
                "description": "Types of tests to generate",
                "items": {
                    "type": "string",
                    "enum": ["positive", "negative", "boundary", "security", "performance"]
                },
                "default": ["positive", "negative"]
            },
            "max_cases_per_endpoint": {
                "type": "integer",
                "description": "Maximum test cases per endpoint",
                "default": 5
            },
            "include_validation_rules": {
                "type": "boolean",
                "description": "Whether to include validation rules in test cases",
                "default": True
            }
        }
    
    def _get_required_parameters(self) -> list:
        """Get required parameters"""
        return ["api_spec"]
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema in OpenAI function calling format
        
        Returns:
            OpenAI function schema
        """
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': self._build_parameters_schema(),
                    'required': self._get_required_parameters()
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Generate test cases from API specification
        
        Args:
            api_spec: API specification
            base_url: Base URL
            test_types: Types of tests to generate
            max_cases_per_endpoint: Maximum cases per endpoint
            include_validation_rules: Whether to include validation rules
            
        Returns:
            Generated test cases
        """
        try:
            # Extract parameters
            api_spec = kwargs.get('api_spec')
            base_url = kwargs.get('base_url', '')
            test_types = kwargs.get('test_types', ['positive', 'negative'])
            max_cases = kwargs.get('max_cases_per_endpoint', 5)
            include_rules = kwargs.get('include_validation_rules', True)
            
            # Validate API spec
            if not isinstance(api_spec, dict):
                raise ValidationError("api_spec must be a dictionary")
            
            # Generate test cases
            test_cases = self._generate_test_cases(
                api_spec=api_spec,
                base_url=base_url,
                test_types=test_types,
                max_cases=max_cases,
                include_rules=include_rules
            )
            
            # Build result
            result_data = {
                'test_cases': test_cases,
                'summary': {
                    'total_cases': len(test_cases),
                    'endpoints_covered': len(set(case['endpoint'] for case in test_cases)),
                    'test_types': test_types
                },
                'api_info': {
                    'title': api_spec.get('info', {}).get('title', 'Unknown API'),
                    'version': api_spec.get('info', {}).get('version', 'Unknown'),
                    'endpoint_count': len(api_spec.get('paths', {}))
                }
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'total_cases': len(test_cases),
                    'endpoints_covered': result_data['summary']['endpoints_covered']
                }
            )
            
        except Exception as e:
            logger.error(f"Test case generation failed: {str(e)}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )
    
    def _generate_test_cases(
        self,
        api_spec: Dict[str, Any],
        base_url: str,
        test_types: List[str],
        max_cases: int,
        include_rules: bool
    ) -> List[Dict[str, Any]]:
        """Generate test cases from API spec"""
        test_cases = []
        paths = api_spec.get('paths', {})
        cases_per_type = {t: 0 for t in test_types}
        
        for path, path_info in paths.items():
            for method, method_info in path_info.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    continue
                
                # Generate test cases for this endpoint
                endpoint_cases = self._generate_endpoint_test_cases(
                    path=path,
                    method=method,
                    details=method_info,
                    base_url=base_url,
                    test_types=test_types,
                    max_cases=max_cases,
                    include_rules=include_rules,
                    cases_per_type=cases_per_type
                )
                
                test_cases.extend(endpoint_cases)
        
        return test_cases
    
    def _generate_endpoint_test_cases(
        self,
        path: str,
        method: str,
        details: Dict[str, Any],
        base_url: str,
        test_types: List[str],
        max_cases: int,
        include_rules: bool,
        cases_per_type: Dict[str, int] = None
    ) -> List[Dict[str, Any]]:
        """Generate test cases for a single endpoint"""
        test_cases = []
        if cases_per_type is None:
            cases_per_type = {}
        
        # Generate positive test cases
        if 'positive' in test_types and cases_per_type.get('positive', 0) < max_cases:
            positive_cases = self._generate_positive_test_cases(
                path=path,
                method=method,
                details=details,
                base_url=base_url,
                max_cases=max_cases,
                include_rules=include_rules
            )
            for case in positive_cases:
                if cases_per_type.get('positive', 0) < max_cases:
                    test_cases.append(case)
                    cases_per_type['positive'] = cases_per_type.get('positive', 0) + 1
        
        # Generate negative test cases
        if 'negative' in test_types and cases_per_type.get('negative', 0) < max_cases:
            negative_cases = self._generate_negative_test_cases(
                path=path,
                method=method,
                details=details,
                base_url=base_url,
                max_cases=max_cases,
                include_rules=include_rules
            )
            for case in negative_cases:
                if cases_per_type.get('negative', 0) < max_cases:
                    test_cases.append(case)
                    cases_per_type['negative'] = cases_per_type.get('negative', 0) + 1
        
        # Generate boundary test cases
        if 'boundary' in test_types and cases_per_type.get('boundary', 0) < max_cases:
            boundary_cases = self._generate_boundary_test_cases(
                path=path,
                method=method,
                details=details,
                base_url=base_url,
                max_cases=max_cases,
                include_rules=include_rules
            )
            for case in boundary_cases:
                if cases_per_type.get('boundary', 0) < max_cases:
                    test_cases.append(case)
                    cases_per_type['boundary'] = cases_per_type.get('boundary', 0) + 1
        
        return test_cases
    
    def _generate_positive_test_cases(
        self,
        path: str,
        method: str,
        details: Dict[str, Any],
        base_url: str,
        max_cases: int,
        include_rules: bool
    ) -> List[Dict[str, Any]]:
        """Generate positive (happy path) test cases"""
        test_cases = []
        
        # Build full URL
        full_url = self._build_full_url(base_url, path)
        
        # Get request body schema
        request_body = details.get('requestBody', {})
        parameters = details.get('parameters', [])
        
        # Generate test data
        test_data = self._generate_test_data_from_schema(details)
        
        # Generate validation rules
        validation_rules = []
        if include_rules:
            validation_rules = self._generate_validation_rules_from_schema(details, method)
        
        # Get expected status
        expected_status = self._get_expected_status_from_schema(details, method)
        
        # Create test case
        test_case = {
            'name': f"{method.upper()} {path} - Positive Test",
            'description': f"Positive test for {method.upper()} {path}",
            'endpoint': path,
            'method': method.upper(),
            'url': full_url,
            'test_type': 'positive',
            'priority': 'high',
            'steps': [
                f"Send {method.upper()} request to {full_url}",
                "Verify response status code",
                "Verify response structure if applicable"
            ],
            'expected_result': f"Response status code should be {expected_status}",
            'request_data': test_data,
            'validation_rules': validation_rules,
            'expected_status': expected_status
        }
        
        test_cases.append(test_case)
        
        # Generate additional positive cases with different data
        additional_cases = min(max_cases - 1, 2)  # Limit additional cases
        for i in range(additional_cases):
            alt_test_data = self._generate_alternative_test_data(test_data)
            
            alt_case = test_case.copy()
            alt_case['name'] = f"{method.upper()} {path} - Positive Test {i + 2}"
            alt_case['request_data'] = alt_test_data
            alt_case['description'] = f"Alternative positive test for {method.upper()} {path}"
            
            test_cases.append(alt_case)
        
        return test_cases
    
    def _generate_negative_test_cases(
        self,
        path: str,
        method: str,
        details: Dict[str, Any],
        base_url: str,
        max_cases: int,
        include_rules: bool
    ) -> List[Dict[str, Any]]:
        """Generate negative test cases"""
        test_cases = []
        
        # Build full URL
        full_url = self._build_full_url(base_url, path)
        
        # Get request body schema for generating invalid data
        request_body = details.get('requestBody', {})
        parameters = details.get('parameters', [])
        
        # Common negative test scenarios
        negative_scenarios = [
            {
                'name': 'Missing Required Fields',
                'description': 'Test with missing required fields',
                'data_generator': self._generate_missing_required_data
            },
            {
                'name': 'Invalid Data Types',
                'description': 'Test with invalid data types',
                'data_generator': self._generate_invalid_type_data
            },
            {
                'name': 'Out of Range Values',
                'description': 'Test with values outside allowed range',
                'data_generator': self._generate_out_of_range_data
            },
            {
                'name': 'Malformed Data',
                'description': 'Test with malformed or corrupted data',
                'data_generator': self._generate_malformed_data
            }
        ]
        
        # Generate test cases for each scenario
        for i, scenario in enumerate(negative_scenarios):
            if i >= max_cases:
                break
            
            # Generate invalid test data
            test_data = scenario['data_generator'](details)
            
            # Create test case
            test_case = {
                'name': f"{method.upper()} {path} - {scenario['name']}",
                'description': scenario['description'],
                'endpoint': path,
                'method': method.upper(),
                'url': full_url,
                'test_type': 'negative',
                'priority': 'medium',
                'steps': [
                    f"Send {method.upper()} request to {full_url} with {scenario['name'].lower()}",
                    "Verify error response"
                ],
                'expected_result': "Should return appropriate error status code (4xx)",
                'request_data': test_data,
                'validation_rules': [
                    {
                        'type': 'status_code',
                        'operator': 'greater_than_or_equal',
                        'expected': 400
                    },
                    {
                        'type': 'status_code',
                        'operator': 'less_than',
                        'expected': 500
                    }
                ] if include_rules else [],
                'expected_status': 400  # Default to 400 Bad Request
            }
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _generate_boundary_test_cases(
        self,
        path: str,
        method: str,
        details: Dict[str, Any],
        base_url: str,
        max_cases: int,
        include_rules: bool
    ) -> List[Dict[str, Any]]:
        """Generate boundary test cases"""
        test_cases = []
        
        # Build full URL
        full_url = self._build_full_url(base_url, path)
        
        # Get schema information for boundary values
        schema = self._extract_schema_from_details(details)
        
        # Generate boundary test data
        boundary_data = self._generate_boundary_test_data(schema)
        
        if boundary_data:
            test_case = {
                'name': f"{method.upper()} {path} - Boundary Test",
                'description': f"Boundary value test for {method.upper()} {path}",
                'endpoint': path,
                'method': method.upper(),
                'url': full_url,
                'test_type': 'boundary',
                'priority': 'medium',
                'steps': [
                    f"Send {method.upper()} request to {full_url} with boundary values",
                    "Verify response handles boundary conditions correctly"
                ],
                'expected_result': "Should handle boundary values appropriately",
                'request_data': boundary_data,
                'validation_rules': [] if not include_rules else [
                    {
                        'type': 'status_code',
                        'expected': self._get_expected_status_from_schema(details, method)
                    }
                ],
                'expected_status': self._get_expected_status_from_schema(details, method)
            }
            
            test_cases.append(test_case)
        
        return test_cases
    
    def _build_full_url(self, base_url: str, path: str) -> str:
        """Build full URL from base URL and path"""
        if not base_url:
            return path
        
        # Ensure base_url ends with slash if path doesn't start with slash
        if base_url.endswith('/') and path.startswith('/'):
            path = path[1:]
        elif not base_url.endswith('/') and not path.startswith('/'):
            path = '/' + path
        
        return base_url + path
    
    def _generate_test_data_from_schema(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test data from schema"""
        # Extract schema from request body
        request_body = details.get('requestBody', {})
        content = request_body.get('content', {})
        
        # Look for JSON schema
        json_schema = None
        for content_type, content_info in content.items():
            if 'application/json' in content_type:
                json_schema = content_info.get('schema')
                break
        
        if json_schema:
            return self._generate_data_from_json_schema(json_schema)
        
        # If no JSON schema, check parameters
        parameters = details.get('parameters', [])
        if parameters:
            return self._generate_data_from_parameters(parameters)
        
        # Return empty dict if no schema found
        return {}
    
    def _generate_data_from_json_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data from JSON schema"""
        data = {}
        
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get('type')
            
            # Generate data based on type
            if prop_type == 'string':
                # Check for format or enum
                if 'enum' in prop_schema:
                    data[prop_name] = self.faker.random_element(prop_schema['enum'])
                elif prop_schema.get('format') == 'email':
                    data[prop_name] = self.faker.email()
                elif prop_schema.get('format') == 'date-time':
                    data[prop_name] = self.faker.iso8601()
                else:
                    # Generate string with appropriate length
                    min_length = prop_schema.get('minLength', 1)
                    max_length = prop_schema.get('maxLength', 50)
                    length = self.faker.random_int(min=min_length, max=max_length)
                    data[prop_name] = self.faker.pystr(min_chars=length, max_chars=length)
            
            elif prop_type == 'integer':
                min_val = prop_schema.get('minimum', 0)
                max_val = prop_schema.get('maximum', 100)
                data[prop_name] = self.faker.random_int(min=min_val, max=max_val)
            
            elif prop_type == 'number':
                min_val = prop_schema.get('minimum', 0.0)
                max_val = prop_schema.get('maximum', 100.0)
                data[prop_name] = self.faker.pyfloat(min_value=min_val, max_value=max_val)
            
            elif prop_type == 'boolean':
                data[prop_name] = self.faker.boolean()
            
            elif prop_type == 'array':
                items_schema = prop_schema.get('items', {})
                min_items = prop_schema.get('minItems', 1)
                max_items = prop_schema.get('maxItems', 3)
                item_count = self.faker.random_int(min=min_items, max=max_items)
                
                # Generate array items
                array_data = []
                for _ in range(item_count):
                    if items_schema.get('type') == 'string':
                        array_data.append(self.faker.word())
                    elif items_schema.get('type') == 'integer':
                        array_data.append(self.faker.random_int())
                    else:
                        array_data.append(None)
                
                data[prop_name] = array_data
            
            elif prop_type == 'object':
                # Recursively generate object data
                data[prop_name] = self._generate_data_from_json_schema(prop_schema)
        
        return data
    
    def _generate_data_from_parameters(self, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate data from parameters"""
        data = {}
        
        for param in parameters:
            param_name = param.get('name')
            param_in = param.get('in', 'query')
            param_schema = param.get('schema', {})
            
            # Only generate data for query/path/header parameters
            if param_in in ['query', 'path', 'header']:
                param_type = param_schema.get('type', 'string')
                
                if param_type == 'string':
                    data[param_name] = self.faker.word()
                elif param_type == 'integer':
                    data[param_name] = self.faker.random_int()
                elif param_type == 'boolean':
                    data[param_name] = self.faker.boolean()
        
        return data
    
    def _generate_alternative_test_data(self, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alternative test data"""
        # Create a copy and modify some values
        alternative_data = original_data.copy()
        
        for key, value in alternative_data.items():
            if isinstance(value, bool):
                # Flip boolean (check bool before int, as bool is subclass of int)
                alternative_data[key] = not value
            elif isinstance(value, str):
                # Modify string by appending "_alt"
                alternative_data[key] = value + "_alt"
            elif isinstance(value, int):
                # Modify integer by adding 1
                alternative_data[key] = value + 1
            elif isinstance(value, float):
                # Modify float by adding 1.0
                alternative_data[key] = value + 1.0
        
        return alternative_data
    
    def _generate_missing_required_data(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data with missing required fields"""
        # Start with valid data
        valid_data = self._generate_test_data_from_schema(details)
        
        # Remove some required fields
        request_body = details.get('requestBody', {})
        content = request_body.get('content', {})
        
        for content_type, content_info in content.items():
            if 'application/json' in content_type:
                schema = content_info.get('schema', {})
                required = schema.get('required', [])
                
                # Remove first required field if exists
                if required and required[0] in valid_data:
                    del valid_data[required[0]]
                    break
        
        return valid_data
    
    def _generate_invalid_type_data(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data with invalid types"""
        valid_data = self._generate_test_data_from_schema(details)
        
        # Change type of first field
        for key, value in valid_data.items():
            if isinstance(value, str):
                valid_data[key] = 12345  # Change to integer
                break
            elif isinstance(value, int):
                valid_data[key] = "invalid_string"  # Change to string
                break
        
        return valid_data
    
    def _generate_out_of_range_data(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data with out of range values"""
        valid_data = self._generate_test_data_from_schema(details)
        
        # Find a numeric field and set out of range value
        for key, value in valid_data.items():
            if isinstance(value, int):
                valid_data[key] = 999999  # Large out of range value
                break
            elif isinstance(value, float):
                valid_data[key] = 999999.99  # Large out of range value
                break
        
        return valid_data
    
    def _generate_malformed_data(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate malformed data"""
        # Return obviously malformed data
        return {
            'malformed': True,
            'invalid_structure': [1, 2, 3],
            'nested': {
                'deeply': {
                    'malformed': 'data'
                }
            }
        }
    
    def _generate_boundary_test_data(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate boundary test data"""
        # This is a simplified implementation
        # In a real implementation, you would analyze the schema for min/max values
        # and generate data at the boundaries
        
        data = {}
        properties = schema.get('properties', {})
        
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get('type')
            
            if prop_type == 'integer':
                min_val = prop_schema.get('minimum')
                max_val = prop_schema.get('maximum')
                
                if min_val is not None:
                    data[prop_name] = min_val  # Minimum boundary
                elif max_val is not None:
                    data[prop_name] = max_val  # Maximum boundary
            
            elif prop_type == 'string':
                min_length = prop_schema.get('minLength')
                max_length = prop_schema.get('maxLength')
                
                if min_length is not None:
                    # String at minimum length
                    data[prop_name] = 'a' * min_length
                elif max_length is not None:
                    # String at maximum length
                    data[prop_name] = 'a' * max_length
        
        return data
    
    def _extract_schema_from_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Extract schema from endpoint details"""
        request_body = details.get('requestBody', {})
        content = request_body.get('content', {})
        
        for content_type, content_info in content.items():
            if 'application/json' in content_type:
                return content_info.get('schema', {})
        
        return {}
    
    def _generate_validation_rules_from_schema(
        self,
        details: Dict[str, Any],
        method: str
    ) -> List[Dict[str, Any]]:
        """Generate validation rules from schema"""
        rules = []
        
        # Always validate status code
        expected_status = self._get_expected_status_from_schema(details, method)
        rules.append({
            'type': 'status_code',
            'expected': expected_status
        })
        
        # Add response time validation for performance
        rules.append({
            'type': 'response_time',
            'value': 5.0  # 5 seconds max
        })
        
        return rules
    
    def _get_expected_status_from_schema(
        self,
        details: Dict[str, Any],
        method: str
    ) -> int:
        """Get expected status code from schema"""
        # Default status codes based on HTTP method
        default_status_codes = {
            'GET': 200,
            'POST': 201,
            'PUT': 200,
            'DELETE': 204,
            'PATCH': 200,
            'HEAD': 200,
            'OPTIONS': 200
        }
        
        return default_status_codes.get(method.upper(), 200)