"""
API test orchestrator tool that combines HTTP client and validation tools
"""

from typing import Dict, Any, List
import logging
import asyncio

from core.tools.base_tool import BaseTool, ToolResult
from core.tools.api.http_client import HTTPClientTool
from core.tools.validation.response_validator import ResponseValidatorTool

logger = logging.getLogger(__name__)


class APITestOrchestratorTool(BaseTool):
    """API test orchestrator that combines HTTP client and validation"""
    
    def __init__(self) -> None:
        super().__init__(
            name="api_test_orchestrator",
            description="Orchestrates API testing by combining HTTP requests and validation",
            version="1.0.0",
            timeout=120
        )
        
        # Initialize component tools
        self.http_client = HTTPClientTool()
        self.validator = ResponseValidatorTool()
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        """Build parameters schema"""
        return {
            "url": {
                "type": "string",
                "description": "API endpoint URL"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                "description": "HTTP method",
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "description": "Request headers",
                "additionalProperties": {"type": "string"}
            },
            "body": {
                "type": ["object", "string", "null"],
                "description": "Request body (JSON, form data, etc.)"
            },
            "params": {
                "type": "object",
                "description": "Query parameters",
                "additionalProperties": {"type": "string"}
            },
            "expected_status": {
                "type": "integer",
                "description": "Expected HTTP status code"
            },
            "validation_rules": {
                "type": "array",
                "description": "Validation rules",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["status_code", "response_time", "json_schema", 
                                    "json_path", "regex", "contains", "header", "content_type"],
                            "description": "Validation type"
                        },
                        "value": {
                            "type": ["string", "integer", "object"],
                            "description": "Validation value"
                        },
                        "path": {
                            "type": "string",
                            "description": "JSON path (for json_path type)"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Regular expression (for regex type)"
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
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds",
                "default": 30
            },
            "follow_redirects": {
                "type": "boolean",
                "description": "Whether to follow redirects",
                "default": True
            },
            "verify_ssl": {
                "type": "boolean",
                "description": "Whether to verify SSL certificates",
                "default": True
            },
            "extract_variables": {
                "type": "object",
                "description": "Variables to extract from response",
                "additionalProperties": {
                    "type": "string",
                    "description": "JSON path to extract value from"
                }
            },
            "strict_validation": {
                "type": "boolean",
                "description": "Whether to fail on first validation error",
                "default": False
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        """Get required parameters"""
        return ["url", "method"]
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute API test with validation
        
        Args:
            url: API endpoint URL
            method: HTTP method
            headers: Request headers
            body: Request body
            params: Query parameters
            expected_status: Expected HTTP status code
            validation_rules: Validation rules
            timeout: Request timeout
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL
            extract_variables: Variables to extract
            strict_validation: Whether to fail on first error
            
        Returns:
            Test execution results
        """
        try:
            # Extract parameters
            url = kwargs.get('url')
            method = kwargs.get('method', 'GET').upper()
            headers = kwargs.get('headers', {})
            body = kwargs.get('body')
            params = kwargs.get('params', {})
            expected_status = kwargs.get('expected_status')
            validation_rules = kwargs.get('validation_rules', [])
            timeout = kwargs.get('timeout', 30)
            follow_redirects = kwargs.get('follow_redirects', True)
            verify_ssl = kwargs.get('verify_ssl', True)
            extract_variables = kwargs.get('extract_variables', {})
            strict_validation = kwargs.get('strict_validation', False)
            
            # Add expected status to validation rules if provided
            if expected_status and not any(
                rule.get('type') == 'status_code' for rule in validation_rules
            ):
                validation_rules.append({
                    'type': 'status_code',
                    'expected': expected_status
                })
            
            # Execute HTTP request
            http_result = await self.http_client.execute(
                url=url,
                method=method,
                headers=headers,
                body=body,
                params=params,
                timeout=timeout,
                follow_redirects=follow_redirects,
                verify_ssl=verify_ssl
            )
            
            if not http_result.success:
                return ToolResult(
                    success=False,
                    data={
                        'http_request_failed': True,
                        'error': http_result.error
                    },
                    error=f"HTTP request failed: {http_result.error}"
                )
            
            # Extract variables if requested
            extracted_vars = {}
            if extract_variables and http_result.data.get('body'):
                extracted_vars = self._extract_variables(
                    response_data=http_result.data,
                    variable_defs=extract_variables
                )
            
            # Validate response if rules provided
            validation_result = None
            if validation_rules:
                validation_result = await self.validator.execute(
                    response_data=http_result.data,
                    validation_rules=validation_rules,
                    strict_mode=strict_validation
                )
                
                if not validation_result.success:
                    return ToolResult(
                        success=False,
                        data={
                            'http_response': http_result.data,
                            'validation_result': validation_result.data,
                            'extracted_variables': extracted_vars
                        },
                        error="Response validation failed"
                    )
            
            # Build final result
            result_data = {
                'http_response': http_result.data,
                'validation_result': validation_result.data if validation_result else None,
                'extracted_variables': extracted_vars,
                'test_passed': validation_result is None or validation_result.data.get('overall_passed', True),
                'metadata': {
                    'url': url,
                    'method': method,
                    'response_time': http_result.data.get('elapsed_time', 0),
                    'status_code': http_result.data.get('status_code')
                }
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'status_code': http_result.data.get('status_code'),
                    'response_time': http_result.data.get('elapsed_time', 0),
                    'test_passed': result_data['test_passed']
                }
            )
            
        except Exception as e:
            logger.error(f"API test execution failed: {str(e)}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )
    
    async def test_multiple_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        parallel: bool = False,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Test multiple API endpoints
        
        Args:
            endpoints: List of endpoint configurations
            parallel: Whether to execute tests in parallel
            max_concurrent: Maximum concurrent tests (if parallel)
            
        Returns:
            List of test results
        """
        if not parallel:
            # Sequential execution
            results = []
            for endpoint_config in endpoints:
                try:
                    result = await self.execute(**endpoint_config)
                    results.append(result.to_dict())
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'endpoint': endpoint_config.get('url', 'unknown')
                    })
            return results
        
        else:
            # Parallel execution with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            results = []
            
            async def execute_with_semaphore(config: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    try:
                        result = await self.execute(**config)
                        return result.to_dict()
                    except Exception as e:
                        return {
                            'success': False,
                            'error': str(e),
                            'endpoint': config.get('url', 'unknown')
                        }
            
            # Create tasks
            tasks = [execute_with_semaphore(config) for config in endpoints]
            
            # Execute in parallel
            results = await asyncio.gather(*tasks)
            return results
    
    def _extract_variables(
        self,
        response_data: Dict[str, Any],
        variable_defs: Dict[str, str]
    ) -> Dict[str, Any]:
        """Extract variables from response using JSON path"""
        extracted: Dict[str, Any] = {}
        response_body = response_data.get('body')
        
        if not response_body or not isinstance(response_body, dict):
            return extracted
        
        try:
            from jsonpath_ng import parse as jsonpath_parse
            
            for var_name, json_path in variable_defs.items():
                try:
                    jsonpath_expr = jsonpath_parse(json_path)
                    matches = [match.value for match in jsonpath_expr.find(response_body)]
                    
                    if matches:
                        extracted[var_name] = matches[0]
                    else:
                        extracted[var_name] = None
                        
                except Exception as e:
                    logger.warning(f"Failed to extract variable '{var_name}' with path '{json_path}': {str(e)}")
                    extracted[var_name] = None
        
        except ImportError:
            logger.warning("jsonpath-ng not available, variable extraction disabled")
        
        return extracted
    
    async def execute_simple_test(
        self,
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        max_response_time: float = 5.0
    ) -> ToolResult:
        """
        Execute a simple API test
        
        Args:
            url: API endpoint URL
            method: HTTP method
            expected_status: Expected status code
            max_response_time: Maximum response time in seconds
            
        Returns:
            Test result
        """
        validation_rules = [
            {
                'type': 'status_code',
                'expected': expected_status
            },
            {
                'type': 'response_time',
                'value': max_response_time
            }
        ]
        
        return await self.execute(
            url=url,
            method=method,
            expected_status=expected_status,
            validation_rules=validation_rules
        )