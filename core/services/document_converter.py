"""
Document Converter - Convert documents to Markdown for knowledge base

Only handles knowledge-type documents: PRD, API_DOC.
"""
import json
import yaml
from typing import Dict, Any, Optional
from shared.constants import DocType


class DocumentConverter:
    """
    Document to Markdown converter
    
    Only converts knowledge-type documents (PRD, API_DOC).
    Business data (test cases, executions) are not stored in knowledge base.
    """
    
    @staticmethod
    def prd_to_markdown(
        title: str,
        content: str,
        project_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert PRD document to Markdown.
        PRD documents are stored directly without parsing.
        
        Args:
            title: Document title
            content: Raw PRD content (Markdown/Text)
            project_id: Project ID
            metadata: Additional metadata
            
        Returns:
            Dict with content and metadata
        """
        result_metadata = {
            'doc_type': DocType.PRD,
            'title': title,
            'project_id': project_id,
        }
        
        if metadata:
            result_metadata.update({
                'version': metadata.get('version'),
                'author': metadata.get('author'),
                'tags': metadata.get('tags', []),
            })
        
        return {
            'content': content,
            'metadata': result_metadata
        }
    
    @staticmethod
    def openapi_to_markdown(
        spec_content: str,
        project_id: int,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert OpenAPI/Swagger specification to Markdown.
        Supports OpenAPI 3.0 and Swagger 2.0 in JSON or YAML format.
        
        Args:
            spec_content: OpenAPI/Swagger spec content (JSON or YAML)
            project_id: Project ID
            title: Document title (optional, extracted from spec if not provided)
            metadata: Additional metadata
            
        Returns:
            Dict with content and metadata
        """
        spec = DocumentConverter._parse_openapi_spec(spec_content)
        
        if spec is None:
            return {
                'content': spec_content,
                'metadata': {
                    'doc_type': DocType.API_DOC,
                    'title': title or 'API Document',
                    'project_id': project_id,
                    'parse_error': True,
                }
            }
        
        info = spec.get('info', {})
        doc_title = title or info.get('title', 'API Document')
        version = info.get('version', '')
        description = info.get('description', '')
        
        base_url = DocumentConverter._extract_base_url(spec)
        paths = spec.get('paths', {})
        api_count = len(paths)
        
        content_parts = [f"# {doc_title}\n"]
        
        if description:
            content_parts.append(f"\n## Description\n\n{description}\n")
        
        content_parts.append(f"\n## Basic Info\n")
        content_parts.append(f"- **Version**: {version}\n")
        if base_url:
            content_parts.append(f"- **Base URL**: {base_url}\n")
        content_parts.append(f"- **API Count**: {api_count}\n")
        
        if paths:
            content_parts.append("\n## API Endpoints\n")
            for path, methods in paths.items():
                content_parts.append(f"\n### `{path}`\n")
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        method_desc = details.get('summary', details.get('description', ''))
                        content_parts.append(f"\n#### {method.upper()}\n")
                        if method_desc:
                            content_parts.append(f"{method_desc}\n")
                        
                        if 'parameters' in details:
                            content_parts.append("\n**Parameters:**\n")
                            for param in details['parameters']:
                                param_name = param.get('name', '')
                                param_in = param.get('in', '')
                                param_required = 'required' if param.get('required') else 'optional'
                                param_desc = param.get('description', '')
                                content_parts.append(f"- `{param_name}` ({param_in}, {param_required}): {param_desc}\n")
                        
                        if 'requestBody' in details:
                            content_parts.append("\n**Request Body:**\n")
                            request_body = details['requestBody']
                            rb_desc = request_body.get('description', '')
                            if rb_desc:
                                content_parts.append(f"{rb_desc}\n")
                            content = request_body.get('content', {})
                            for content_type, schema_info in content.items():
                                content_parts.append(f"- Content-Type: {content_type}\n")
                        
                        if 'responses' in details:
                            content_parts.append("\n**Responses:**\n")
                            for status_code, response in details['responses'].items():
                                resp_desc = response.get('description', '')
                                content_parts.append(f"- `{status_code}`: {resp_desc}\n")
        
        result_metadata = {
            'doc_type': DocType.API_DOC,
            'title': doc_title,
            'project_id': project_id,
            'api_count': api_count,
            'base_url': base_url,
            'api_version': version,
        }
        
        if metadata:
            result_metadata.update({
                'author': metadata.get('author'),
                'tags': metadata.get('tags', []),
            })
        
        return {
            'content': ''.join(content_parts),
            'metadata': result_metadata
        }
    
    @staticmethod
    def _parse_openapi_spec(content: str) -> Optional[Dict[str, Any]]:
        """Parse OpenAPI/Swagger spec from JSON or YAML."""
        content = content.strip()
        
        try:
            if content.startswith('{') or content.startswith('['):
                result = json.loads(content)
            else:
                result = yaml.safe_load(content)
            
            return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, yaml.YAMLError):
            return None
    
    @staticmethod
    def _extract_base_url(spec: Dict[str, Any]) -> str:
        """Extract base URL from OpenAPI spec."""
        if 'servers' in spec:
            servers = spec['servers']
            if servers and len(servers) > 0:
                return str(servers[0].get('url', ''))
        elif 'host' in spec:
            host = spec['host']
            base_path = spec.get('basePath', '')
            schemes = spec.get('schemes', ['https'])
            scheme = schemes[0] if schemes else 'https'
            return f"{scheme}://{host}{base_path}"
        return ''
    
    @staticmethod
    def convert_uploaded_document(
        doc_type: str,
        title: str,
        content: str,
        project_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Unified entry point for converting uploaded documents.
        
        Args:
            doc_type: Document type (prd, api_doc)
            title: Document title
            content: Document content
            project_id: Project ID
            metadata: Additional metadata
            
        Returns:
            Dict with content and metadata
        """
        if doc_type == DocType.PRD:
            return DocumentConverter.prd_to_markdown(
                title=title,
                content=content,
                project_id=project_id,
                metadata=metadata
            )
        elif doc_type == DocType.API_DOC:
            return DocumentConverter.openapi_to_markdown(
                spec_content=content,
                project_id=project_id,
                title=title,
                metadata=metadata
            )
        else:
            raise ValueError(f"Unsupported document type: {doc_type}. Supported types: {', '.join(DocType.ALL)}")