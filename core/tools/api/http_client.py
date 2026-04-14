"""
HTTP client tool for making API requests
"""

import httpx
import json
from typing import Dict, Any, Optional
import logging
from urllib.parse import urlparse, urljoin

from core.tools.base_tool import BaseTool, ToolResult
from shared.exceptions import RequestError, ValidationError
from shared.utils.validation import validate_url

logger = logging.getLogger(__name__)


class HTTPClientTool(BaseTool):
    """HTTP client tool for making API requests"""
    
    def __init__(self):
        super().__init__(
            name="http_client",
            description="HTTP client for making API requests with support for various methods and authentication",
            version="1.0.0",
            timeout=60
        )
        
        # Default timeout for requests
        self.default_timeout = 60
        
        # Default headers
        self.default_headers = {
            'User-Agent': 'TestAutomation/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
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
            }
        }
    
    def _get_required_parameters(self) -> list:
        """Get required parameters"""
        return ["url", "method"]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute HTTP request
        
        Args:
            url: API endpoint URL
            method: HTTP method
            headers: Request headers
            body: Request body
            params: Query parameters
            timeout: Request timeout
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL
            
        Returns:
            HTTP response data
        """
        try:
            # Extract parameters
            url = kwargs.get('url')
            method = kwargs.get('method', 'GET').upper()
            headers = kwargs.get('headers', {})
            body = kwargs.get('body')
            params = kwargs.get('params', {})
            timeout = kwargs.get('timeout', 30)
            follow_redirects = kwargs.get('follow_redirects', True)
            verify_ssl = kwargs.get('verify_ssl', True)
            
            # Validate URL
            if not validate_url(url):  # type: ignore[arg-type]
                raise ValidationError(f"Invalid URL: {url}")
            
            # Prepare request
            request_data = self._prepare_request(
                url=url,  # type: ignore[arg-type]
                method=method,
                headers=headers,
                body=body,
                params=params
            )
            
            # Make request
            response = await self._make_request(
                request_data=request_data,
                timeout=timeout,
                follow_redirects=follow_redirects,
                verify_ssl=verify_ssl
            )
            
            # Parse response
            response_data = self._parse_response(response)
            
            # Build result
            result_data = {
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': response_data,
                'elapsed_time': response.elapsed.total_seconds(),
                'request_info': {
                    'headers': request_data['headers'],
                    'params': params
                }
            }
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
            )
            
        except Exception as e:
            logger.error(f"HTTP request failed: {str(e)}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )
    
    def _prepare_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        body: Any,
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Prepare request data"""
        # Merge headers with defaults
        merged_headers = {**self.default_headers, **headers}
        
        # Prepare body
        prepared_body = None
        if body is not None:
            if isinstance(body, dict):
                # Check if we should send as form data
                content_type = merged_headers.get('Content-Type', '').lower()
                if 'application/x-www-form-urlencoded' in content_type:
                    prepared_body = body
                else:
                    prepared_body = json.dumps(body)
            else:
                prepared_body = body
        
        return {
            'url': url,
            'method': method,
            'headers': merged_headers,
            'body': prepared_body,
            'params': params
        }
    
    async def _make_request(
        self,
        request_data: Dict[str, Any],
        timeout: int,
        follow_redirects: bool,
        verify_ssl: bool
    ) -> httpx.Response:
        """Make HTTP request"""
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=follow_redirects,
                verify=verify_ssl
            ) as client:
                # Prepare request arguments
                request_args = {
                    'method': request_data['method'],
                    'url': request_data['url'],
                    'headers': request_data['headers']
                }
                
                # Add params if present
                if request_data.get('params'):
                    request_args['params'] = request_data['params']
                
                # Add body if present
                if request_data.get('body') is not None:
                    request_args['content'] = request_data['body']
                
                # Make request
                response = await client.request(**request_args)
                return response
                
        except httpx.TimeoutException:
            raise RequestError(f"Request timeout after {timeout} seconds")
        except httpx.RequestError as e:
            raise RequestError(f"Request failed: {str(e)}")
        except Exception as e:
            raise RequestError(f"Unexpected error: {str(e)}")
    
    def _parse_response(self, response: httpx.Response) -> Any:
        """Parse HTTP response"""
        try:
            # Try to parse as JSON
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return response.json()
            elif 'text/' in content_type:
                return response.text
            else:
                # Return raw bytes for binary content
                return response.content.decode('utf-8', errors='ignore')
        except Exception:
            # Fallback to text
            return response.text
    
    async def get(self, url: str, **kwargs) -> ToolResult:
        """Convenience method for GET requests"""
        return await self.execute(url=url, method='GET', **kwargs)
    
    async def post(self, url: str, body: Any = None, **kwargs) -> ToolResult:
        """Convenience method for POST requests"""
        return await self.execute(url=url, method='POST', body=body, **kwargs)
    
    async def put(self, url: str, body: Any = None, **kwargs) -> ToolResult:
        """Convenience method for PUT requests"""
        return await self.execute(url=url, method='PUT', body=body, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> ToolResult:
        """Convenience method for DELETE requests"""
        return await self.execute(url=url, method='DELETE', **kwargs)
    
    async def patch(self, url: str, body: Any = None, **kwargs) -> ToolResult:
        """Convenience method for PATCH requests"""
        return await self.execute(url=url, method='PATCH', body=body, **kwargs)