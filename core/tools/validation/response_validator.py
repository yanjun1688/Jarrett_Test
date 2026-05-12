"""
Response validation tool for API testing
"""

import re
import jsonschema
import json
from typing import Dict, Any, List
import logging
from jsonpath_ng import parse as jsonpath_parse

from core.tools.base_tool import BaseTool, ToolResult
from shared.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ResponseValidatorTool(BaseTool):
    """Response validation tool for API testing"""
    
    def __init__(self) -> None:
        super().__init__(
            name="response_validator",
            description="Validate API responses against various rules and schemas",
            version="1.0.0"
        )
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        """Build parameters schema"""
        return {
            "response_data": {
                "type": "object",
                "description": "Response data to validate",
                "properties": {
                    "status_code": {"type": "integer"},
                    "body": {"type": ["object", "string", "array", "null"]},
                    "headers": {"type": "object"}
                },
                "required": ["status_code", "body"]
            },
            "validation_rules": {
                "type": "array",
                "description": "Validation rules to apply",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "status_code", 
                                "response_time", 
                                "json_schema", 
                                "json_path", 
                                "regex", 
                                "contains",
                                "header",
                                "content_type"
                            ],
                            "description": "Validation type"
                        },
                        "value": {
                            "type": ["string", "integer", "object", "array"],
                            "description": "Validation value or pattern"
                        },
                        "path": {
                            "type": "string",
                            "description": "JSON path (for json_path type)"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Regular expression pattern (for regex type)"
                        },
                        "expected": {
                            "type": ["string", "integer", "boolean", "object", "array"],
                            "description": "Expected value"
                        },
                        "operator": {
                            "type": "string",
                            "enum": ["equals", "not_equals", "contains", "not_contains", 
                                    "greater_than", "less_than", "matches", "exists"],
                            "description": "Comparison operator",
                            "default": "equals"
                        }
                    },
                    "required": ["type"]
                }
            },
            "strict_mode": {
                "type": "boolean",
                "description": "Whether to fail on first validation error",
                "default": False
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        """Get required parameters"""
        return ["response_data", "validation_rules"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Validate response against rules
        
        Args:
            response_data: Response data to validate
            validation_rules: List of validation rules
            strict_mode: Whether to fail on first error
            
        Returns:
            Validation results
        """
        try:
            # Extract parameters
            response_data = kwargs.get('response_data')
            validation_rules = kwargs.get('validation_rules', [])
            strict_mode = kwargs.get('strict_mode', False)
            
            # Validate response data structure
            if not isinstance(response_data, dict):
                raise ValidationError("response_data must be a dictionary")
            
            if 'status_code' not in response_data:
                raise ValidationError("response_data must contain 'status_code'")
            
            # Apply validation rules
            validation_results = []
            all_passed = True
            
            for rule in validation_rules:
                try:
                    result = self._apply_validation_rule(rule, response_data)
                    validation_results.append(result)
                    
                    if not result['passed'] and strict_mode:
                        all_passed = False
                        break
                        
                except Exception as e:
                    validation_results.append({
                        'rule': rule,
                        'passed': False,
                        'error': str(e),
                        'message': f"Rule validation failed: {str(e)}"
                    })
                    
                    if strict_mode:
                        all_passed = False
                        break
            
            # Calculate overall result
            passed_count = sum(1 for r in validation_results if r['passed'])
            total_count = len(validation_results)
            
            result_data = {
                'overall_passed': all_passed and (passed_count == total_count),
                'passed_count': passed_count,
                'total_count': total_count,
                'validation_results': validation_results,
                'response_summary': {
                    'status_code': response_data.get('status_code'),
                    'has_body': 'body' in response_data and response_data['body'] is not None
                }
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'passed_count': passed_count,
                    'total_count': total_count
                }
            )
            
        except Exception as e:
            logger.error(f"Response validation failed: {str(e)}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )
    
    def _apply_validation_rule(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a single validation rule"""
        rule_type = rule.get('type')
        
        if not rule_type:
            raise ValidationError("Validation rule must have a 'type'")
        
        # Dispatch to appropriate validation method
        validation_methods = {
            'status_code': self._validate_status_code,
            'response_time': self._validate_response_time,
            'json_schema': self._validate_json_schema,
            'json_path': self._validate_json_path,
            'regex': self._validate_regex,
            'contains': self._validate_contains,
            'header': self._validate_header,
            'content_type': self._validate_content_type
        }
        
        if rule_type not in validation_methods:
            raise ValidationError(f"Unknown validation type: {rule_type}")
        
        try:
            return validation_methods[rule_type](rule, response_data)
        except Exception as e:
            return {
                'rule': rule,
                'passed': False,
                'error': str(e),
                'message': f"{rule_type} validation failed: {str(e)}"
            }
    
    def _validate_status_code(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate status code"""
        actual_status = response_data.get('status_code')
        expected_status = rule.get('expected')
        operator = rule.get('operator', 'equals')
        
        if expected_status is None:
            raise ValidationError("status_code validation requires 'expected' value")
        
        passed = False
        message = ""
        
        if operator == 'equals':
            passed = actual_status == expected_status
            message = f"Status code {actual_status} {'equals' if passed else 'does not equal'} expected {expected_status}"
        elif operator == 'not_equals':
            passed = actual_status != expected_status
            message = f"Status code {actual_status} {'does not equal' if passed else 'equals'} expected {expected_status}"
        elif operator == 'greater_than':
            passed = actual_status > expected_status
            message = f"Status code {actual_status} is {'greater than' if passed else 'not greater than'} {expected_status}"
        elif operator == 'less_than':
            passed = actual_status < expected_status
            message = f"Status code {actual_status} is {'less than' if passed else 'not less than'} {expected_status}"
        else:
            raise ValidationError(f"Unsupported operator for status_code: {operator}")
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'actual': actual_status,
            'expected': expected_status
        }
    
    def _validate_response_time(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate response time"""
        actual_time = response_data.get('elapsed_time')
        max_time = rule.get('value')
        
        if actual_time is None:
            raise ValidationError("Response time not available in response_data")
        
        if max_time is None:
            raise ValidationError("response_time validation requires 'value' (max time in seconds)")
        
        passed = actual_time <= max_time
        message = f"Response time {actual_time:.3f}s is {'within' if passed else 'exceeds'} limit of {max_time}s"
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'actual': actual_time,
            'expected': max_time
        }
    
    def _validate_json_schema(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate JSON schema"""
        schema = rule.get('value')
        response_body = response_data.get('body')
        
        if schema is None:
            raise ValidationError("json_schema validation requires 'value' (JSON schema)")
        
        if response_body is None:
            raise ValidationError("Response body is required for JSON schema validation")
        
        # Convert response body to dict if it's a string
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except json.JSONDecodeError:
                raise ValidationError("Response body is not valid JSON")
        
        # Validate against schema
        try:
            jsonschema.validate(instance=response_body, schema=schema)
            passed = True
            message = "Response body matches JSON schema"
        except jsonschema.ValidationError as e:
            passed = False
            message = f"JSON schema validation failed: {str(e)}"
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'schema': schema
        }
    
    def _validate_json_path(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate JSON path expression"""
        path = rule.get('path')
        expected = rule.get('expected')
        operator = rule.get('operator', 'equals')
        response_body = response_data.get('body')
        
        if path is None:
            raise ValidationError("json_path validation requires 'path'")
        
        if response_body is None:
            raise ValidationError("Response body is required for JSON path validation")
        
        # Convert response body to dict if it's a string
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except json.JSONDecodeError:
                raise ValidationError("Response body is not valid JSON")
        
        # Parse JSON path
        try:
            jsonpath_expr = jsonpath_parse(path)
            matches = [match.value for match in jsonpath_expr.find(response_body)]
        except Exception as e:
            raise ValidationError(f"Invalid JSON path '{path}': {str(e)}")
        
        passed = False
        message = ""
        
        if operator == 'exists':
            passed = len(matches) > 0
            message = f"JSON path '{path}' {'exists' if passed else 'does not exist'} in response"
        elif operator == 'equals':
            if len(matches) == 0:
                message = f"JSON path '{path}' not found in response"
            else:
                passed = matches[0] == expected
                message = f"JSON path '{path}' value {matches[0]} {'equals' if passed else 'does not equal'} expected {expected}"
        elif operator == 'contains':
            if len(matches) == 0:
                message = f"JSON path '{path}' not found in response"
            else:
                passed = expected in matches[0]
                message = f"JSON path '{path}' value {matches[0]} {'contains' if passed else 'does not contain'} expected value {expected}"
        else:
            raise ValidationError(f"Unsupported operator for json_path: {operator}")
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'path': path,
            'matches': matches,
            'expected': expected
        }
    
    def _validate_regex(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate regular expression"""
        pattern = rule.get('pattern')
        response_body = response_data.get('body')
        
        if pattern is None:
            raise ValidationError("regex validation requires 'pattern'")
        
        if response_body is None:
            raise ValidationError("Response body is required for regex validation")
        
        # Convert response body to string if it's not
        if not isinstance(response_body, str):
            response_body = str(response_body)
        
        # Test regex
        try:
            match = re.search(pattern, response_body)
            passed = match is not None
            message = f"Regex pattern {'matches' if passed else 'does not match'} response body"
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern '{pattern}': {str(e)}")
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'pattern': pattern,
            'match': match.group() if match else None
        }
    
    def _validate_contains(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that response contains text"""
        expected = rule.get('expected')
        response_body = response_data.get('body')
        
        if expected is None:
            raise ValidationError("contains validation requires 'expected'")
        
        if response_body is None:
            raise ValidationError("Response body is required for contains validation")
        
        # Convert both to strings
        expected_str = str(expected)
        response_str = str(response_body)
        
        passed = expected_str in response_str
        message = f"Response {'contains' if passed else 'does not contain'} expected text"
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'expected': expected_str,
            'found_at': response_str.find(expected_str) if passed else -1
        }
    
    def _validate_header(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate response header"""
        header_name = rule.get('value')
        expected = rule.get('expected')
        operator = rule.get('operator', 'equals')
        headers = response_data.get('headers', {})
        
        if header_name is None:
            raise ValidationError("header validation requires 'value' (header name)")
        
        actual_value = headers.get(header_name)
        
        passed = False
        message = ""
        
        if operator == 'exists':
            passed = actual_value is not None
            message = f"Header '{header_name}' {'exists' if passed else 'does not exist'}"
        elif operator == 'equals':
            passed = actual_value == expected
            message = f"Header '{header_name}' value '{actual_value}' {'equals' if passed else 'does not equal'} expected '{expected}'"
        elif operator == 'contains':
            if actual_value is None:
                message = f"Header '{header_name}' not found"
            else:
                passed = expected in actual_value
                message = f"Header '{header_name}' {'contains' if passed else 'does not contain'} expected value '{expected}'"
        else:
            raise ValidationError(f"Unsupported operator for header: {operator}")
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'header': header_name,
            'actual': actual_value,
            'expected': expected
        }
    
    def _validate_content_type(
        self,
        rule: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate content type header"""
        expected = rule.get('expected')
        headers = response_data.get('headers', {})
        
        if expected is None:
            raise ValidationError("content_type validation requires 'expected'")
        
        content_type = headers.get('content-type', headers.get('Content-Type', ''))
        
        passed = expected.lower() in content_type.lower()
        message = f"Content type '{content_type}' {'contains' if passed else 'does not contain'} expected '{expected}'"
        
        return {
            'rule': rule,
            'passed': passed,
            'message': message,
            'actual': content_type,
            'expected': expected
        }