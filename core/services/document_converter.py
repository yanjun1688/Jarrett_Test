"""
Document Converter - Convert test cases to Markdown

Uses lazy loading to avoid circular dependencies from core to business apps.
"""
import json
import yaml
from typing import Dict, Any, Optional, Type
from shared.constants import DocType


class DocumentConverter:
    """
    Test case to Markdown document converter
    
    Uses lazy loading to avoid core layer depending on business apps.
    """
    
    @staticmethod
    def _get_model(model_name: str) -> Type[Any]:
        """Lazy load model to avoid circular import"""
        from django.apps import apps
        return apps.get_model(model_name)
    
    @staticmethod
    def feature_test_to_markdown(test_case: Any) -> Dict[str, Any]:
        """
        Convert feature test case to Markdown
        
        Args:
            test_case: FeatureTestCase instance (passed by caller)
        """
        version_str = test_case.version or '未指定'
        pre_steps_str = test_case.pre_steps or '无'
        actual_result_str = test_case.actual_result or '未填写'
        to_confirm_str = test_case.to_confirm or '无'
        
        if test_case.is_passed is True:
            is_passed_str = '✅ 通过'
        elif test_case.is_passed is False:
            is_passed_str = '❌ 未通过'
        else:
            is_passed_str = '⏳ 待验证'
        
        content = f"""# 功能测试用例: {test_case.title}

## 基本信息
- **项目ID**: {test_case.project_id}
- **版本**: {version_str}
- **创建时间**: {test_case.created_at.strftime('%Y-%m-%d %H:%M')}

## 前置步骤
{pre_steps_str}

## 操作步骤
{test_case.steps}

## 预期结果
{test_case.expected_result}

## 实际结果
{actual_result_str}

## 待确定
{to_confirm_str}

## 是否通过
{is_passed_str}
"""
        return {
            'content': content,
            'metadata': {
                'doc_type': 'feature_test',
                'source_id': test_case.id,
                'source_model': 'FeatureTestCase',
                'title': test_case.title,
                'project_id': test_case.project_id,
                'is_passed': test_case.is_passed,
            }
        }
    
    @staticmethod
    def api_test_to_markdown(api_request: Any) -> Dict[str, Any]:
        """
        Convert API test request to Markdown
        
        Args:
            api_request: ApiRequest instance (passed by caller)
        """
        headers_str = json.dumps(api_request.headers or {}, ensure_ascii=False, indent=2)
        body_str = api_request.body or '无'
        description_str = api_request.description or '无描述'
        
        content = f"""# API 测试: {api_request.name}

## 基本信息
- **项目ID**: {api_request.project_id}
- **请求方法**: {api_request.method}
- **URL**: {api_request.url}

## 请求配置
### Headers
```json
{headers_str}
```

### Body
```
{body_str}
```

## 描述
{description_str}
"""
        return {
            'content': content,
            'metadata': {
                'doc_type': 'api_test',
                'source_id': api_request.id,
                'source_model': 'ApiRequest',
                'name': api_request.name,
                'method': api_request.method,
                'url': api_request.url,
                'project_id': api_request.project_id,
            }
        }
    
    @staticmethod
    def ui_test_to_markdown(ui_script: Any) -> Dict[str, Any]:
        """
        Convert UI test script to Markdown
        
        Args:
            ui_script: UITestScript instance (passed by caller)
        """
        description_str = ui_script.description or '无描述'
        actions_str = json.dumps(ui_script.actions or [], ensure_ascii=False, indent=2)
        browser_type_str = getattr(ui_script, 'browser_type', 'chromium') or 'chromium'
        
        content = f"""# UI 测试脚本: {ui_script.name}

## 基本信息
- **项目ID**: {ui_script.project_id}
- **浏览器类型**: {browser_type_str}

## 描述
{description_str}

## 动作列表
```json
{actions_str}
```
"""
        return {
            'content': content,
            'metadata': {
                'doc_type': 'ui_test',
                'source_id': ui_script.id,
                'source_model': 'UITestScript',
                'name': ui_script.name,
                'browser_type': browser_type_str,
                'project_id': ui_script.project_id,
            }
        }
    
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
                return servers[0].get('url', '')
        elif 'host' in spec:
            host = spec['host']
            base_path = spec.get('basePath', '')
            schemes = spec.get('schemes', ['https'])
            scheme = schemes[0] if schemes else 'https'
            return f"{scheme}://{host}{base_path}"
        return ''
    
    @staticmethod
    def _generic_test_to_markdown(
        doc_type: str,
        title: str,
        content: str,
        project_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generic converter for test document types."""
        doc_type_labels = {
            DocType.FEATURE_TEST: '功能测试',
            DocType.API_TEST: 'API 测试',
            DocType.UI_TEST: 'UI 测试',
        }
        
        label = doc_type_labels.get(doc_type, doc_type)
        
        content_parts = [f"# {label}: {title}\n"]
        content_parts.append(f"\n## 基本信息\n")
        content_parts.append(f"- **项目ID**: {project_id}\n")
        
        if metadata:
            if metadata.get('version'):
                content_parts.append(f"- **版本**: {metadata.get('version')}\n")
            if metadata.get('author'):
                content_parts.append(f"- **作者**: {metadata.get('author')}\n")
            tags = metadata.get('tags', [])
            if tags:
                content_parts.append(f"- **标签**: {', '.join(tags)}\n")
        
        content_parts.append(f"\n## 内容\n")
        content_parts.append(content)
        
        result_metadata = {
            'doc_type': doc_type,
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
            'content': ''.join(content_parts),
            'metadata': result_metadata
        }
    
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
        elif doc_type in (DocType.FEATURE_TEST, DocType.API_TEST, DocType.UI_TEST):
            return DocumentConverter._generic_test_to_markdown(
                doc_type=doc_type,
                title=title,
                content=content,
                project_id=project_id,
                metadata=metadata
            )
        else:
            raise ValueError(f"Unsupported document type: {doc_type}. Supported types: prd, api_doc, feature_test, api_test, ui_test")