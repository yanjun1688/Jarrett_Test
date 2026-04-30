"""
YAML到RequestCollection的转换服务
将YAML配置文件转换为数据库中的RequestCollection及相关模型

架构：
- YamlParser: 纯解析层，无 Django 依赖
- YamlToCollectionConverter: 转换层，使用 YamlParser（已废弃，使用 YamlToScriptConverter）
- YamlToScriptConverter: 新的转换层，创建 TestScript
- YamlPersister: 持久化层（本文件）
"""

from __future__ import annotations

import json
import warnings
import yaml
import base64
import logging
import re
import types
from typing import Dict, Any, List, Tuple, Optional, Union, Set
from django.db import transaction
from django.contrib.auth.models import User
from core.models import Project
from testmanager_app.models import (
    RequestCollection,
    ApiRequest,
    CollectionRequest,
    ApiAssertion,
    TestScript
)
from .yaml_parser import YamlParser, YamlValidationError, YamlConfig
from .yaml_validator import YamlValidator

logger = logging.getLogger(__name__)


class YamlToScriptConverter:
    """
    YAML到TestScript的转换器
    
    改造后：YAML上传直接转为 TestScript，不再创建 RequestCollection
    """

    def __init__(self, project_id: int, created_by_id: int):
        self.project_id = project_id
        self.created_by_id = created_by_id
        self.parser = YamlParser()
        self.validator = YamlValidator()

    def convert(self, yaml_content: str, name: str, description: str = '',
                validate_only: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        将YAML转换为TestScript

        Args:
            yaml_content: YAML内容（字符串）
            name: TestScript名称
            description: TestScript描述
            validate_only: 是否仅验证不保存

        Returns:
            (success, result_dict)
        """
        try:
            is_valid, errors, warnings_list = self.validator.validate(yaml_content)
            
            if not is_valid:
                error_messages = '\n'.join([e['message'] for e in errors if e['level'] == 'error'])
                return False, {
                    'error': 'YAML验证失败',
                    'errors': errors,
                    'warnings': warnings_list
                }

            config = self.parser.parse(yaml_content)
            
            preview = self._generate_preview(config, name, description)

            if validate_only:
                return True, {
                    'valid': True,
                    'preview': preview,
                    'validation_result': {
                        'is_valid': True,
                        'errors': errors,
                        'warnings': warnings_list
                    }
                }

            # 创建 TestScript（不再是 RequestCollection）
            result = self._persist_to_database(yaml_content, name, description)

            return True, result

        except YamlValidationError as e:
            return False, {
                'error': f'YAML解析失败: {str(e)}',
            }
        except Exception as e:
            import traceback
            return False, {
                'error': f'转换失败: {str(e)}',
                'detail': traceback.format_exc()
            }

    def convert_from_base64(self, base64_content: str, name: str, description: str = '',
                           validate_only: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """从Base64编码的YAML内容转换"""
        try:
            yaml_content = base64.b64decode(base64_content.encode('utf-8')).decode('utf-8')
            return self.convert(yaml_content, name, description, validate_only)
        except Exception as e:
            return False, {'error': f'Base64解码失败: {str(e)}'}

    def _generate_preview(self, config: Any, name: str, description: str) -> Dict[str, Any]:
        """生成预览信息"""
        from .yaml_parser import YamlConfig
        
        steps_preview = []
        defined_vars: Set[str] = set()
        extracted_vars = set()

        if isinstance(config, YamlConfig):
            defined_vars.update(config.env_vars.keys())
            steps = config.steps
        else:
            if 'env_vars' in config and isinstance(config['env_vars'], dict):
                defined_vars.update(config['env_vars'].keys())
            steps = config.get('steps', [])

        for step_idx, step in enumerate(steps):
            step_info = {
                'order': step_idx,
                'name': step['name'],
                'method': step.get('request', {}).get('method', ''),
                'url': step.get('request', {}).get('url', ''),
                'assertions_count': len(step.get('assertions', [])),
                'extract_vars': []
            }

            for extract in step.get('extract', []):
                var_name = extract.get('name')
                if var_name:
                    step_info['extract_vars'].append(var_name)
                    extracted_vars.add(var_name)

            steps_preview.append(step_info)

        all_used_vars = self._collect_all_used_variables(steps)
        undefined_vars = all_used_vars - defined_vars - extracted_vars

        preview = {
            'name': name,
            'description': description,
            'script_type': 'yaml',
            'total_steps': len(steps),
            'steps_preview': steps_preview,
            'variables': {
                'defined': list(defined_vars),
                'extracted': list(extracted_vars),
                'undefined': list(undefined_vars) if undefined_vars else []
            }
        }
        return preview

    def _collect_all_used_variables(self, steps: List[Dict[str, Any]]) -> set[str]:
        """收集所有使用的变量"""
        import re
        used_vars: set[str] = set()

        for step_idx, step in enumerate(steps):
            request = step.get('request', {})
            base_location = f'steps[{step_idx}].request'

            if 'url' in request:
                self._collect_from_string(request['url'], f'{base_location}.url', used_vars, re)

            if 'headers' in request:
                for key, value in request['headers'].items():
                    self._collect_from_string(value, f'{base_location}.headers.{key}', used_vars, re)

            if 'body' in request:
                self._collect_from_object(request['body'], f'{base_location}.body', used_vars, re)

        return used_vars

    def _collect_from_string(self, text: str, location: str, variables: set[str], re_module: types.ModuleType) -> None:
        """从字符串收集变量"""
        if not isinstance(text, str):
            return  # type: ignore[unreachable]

        var_pattern = re_module.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_\.]*(\s*\|\s*default\s*:\s*"[^"]*")?\s*)}}')
        matches = var_pattern.findall(text)
        for match in matches if matches else []:
            var = match[0].strip()
            if '|' in var:
                var = var.split('|')[0].strip()
            # 提取根变量名
            root_var = var.split('.')[0]
            variables.add(root_var)

    def _collect_from_object(self, obj: Any, base_location: str, variables: set[str], re: types.ModuleType) -> None:
        """递归收集对象中的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f'{base_location}.{key}'
                if isinstance(value, str):
                    self._collect_from_string(value, location, variables, re)
                else:
                    self._collect_from_object(value, location, variables, re)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f'{base_location}[{idx}]'
                if isinstance(item, str):
                    self._collect_from_string(item, location, variables, re)
                else:
                    self._collect_from_object(item, location, variables, re)

    @transaction.atomic
    def _persist_to_database(self, yaml_content: str, name: str, description: str) -> Dict[str, Any]:
        """持久化到数据库 - 创建 TestScript"""
        # 创建 TestScript（不再是 RequestCollection）
        test_script = TestScript.objects.create(
            name=name,
            description=description,
            script_type='yaml',
            content=yaml_content,
            project_id=self.project_id,
            created_by_id=self.created_by_id
        )

        result: Dict[str, Any] = {
            'script_id': test_script.id,
            'name': test_script.name,
            'type': 'yaml',
            'message': 'YAML已保存为测试脚本，请手动执行',
            'created_at': test_script.created_at.isoformat()
        }

        return result

    def validate_only(self, yaml_content: str) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """仅验证YAML，不转换"""
        is_valid, errors, warnings = self.validator.validate(yaml_content)

        preview = None
        if is_valid:
            config = yaml.safe_load(yaml_content)
            preview = self._generate_preview(config, '验证中', '')

        return is_valid, errors, warnings, preview


# ============================================================================
# 以下类已废弃，保留用于兼容
# ============================================================================

class YamlToCollectionConverter:
    """
    YAML到RequestCollection的转换器（使用分离的解析层）
    
    DEPRECATED: 2026-04-15
    请使用 YamlToScriptConverter 替代
    保留原因：兼容现有代码，观察期后删除
    """

    def __init__(self, project_id: int, created_by_id: int):
        warnings.warn(
            "YamlToCollectionConverter is deprecated. Use YamlToScriptConverter instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.project_id = project_id
        self.created_by_id = created_by_id
        self.parser = YamlParser()
        self.validator = YamlValidator()
        self.created_objects: Dict[str, List[Any]] = {
            'request_collections': [],
            'api_requests': [],
            'collection_requests': [],
            'assertions': []
        }

    def convert(self, yaml_content: str, name: str, description: str = '',
                execution_mode: str = 'chain', validate_only: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        将YAML转换为RequestCollection

        Args:
            yaml_content: YAML内容（字符串）
            name: RequestCollection名称
            description: RequestCollection描述
            execution_mode: 执行模式（concurrent/sequential/chain）
            validate_only: 是否仅验证不保存

        Returns:
            (success, result_dict)
        """
        try:
            is_valid, errors, warnings = self.validator.validate(yaml_content)
            
            if not is_valid:
                error_messages = '\n'.join([e['message'] for e in errors if e['level'] == 'error'])
                return False, {
                    'error': 'YAML验证失败',
                    'errors': errors,
                    'warnings': warnings
                }

            config = self.parser.parse(yaml_content)
            
            preview = self._generate_preview(config, name, description, execution_mode)

            if validate_only:
                return True, {
                    'valid': True,
                    'preview': preview,
                    'validation_result': {
                        'is_valid': True,
                        'errors': errors,
                        'warnings': warnings
                    }
                }

            result = self._persist_to_database(config, name, description, execution_mode)

            return True, result

        except YamlValidationError as e:
            return False, {
                'error': f'YAML解析失败: {str(e)}',
            }
        except Exception as e:
            import traceback
            return False, {
                'error': f'转换失败: {str(e)}',
                'detail': traceback.format_exc()
            }

    def convert_from_base64(self, base64_content: str, name: str, description: str = '',
                           execution_mode: str = 'chain', validate_only: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """从Base64编码的YAML内容转换"""
        try:
            yaml_content = base64.b64decode(base64_content.encode('utf-8')).decode('utf-8')
            return self.convert(yaml_content, name, description, execution_mode, validate_only)
        except Exception as e:
            return False, {'error': f'Base64解码失败: {str(e)}'}

    def _generate_preview(
        self,
        config: Union[YamlConfig, Dict[str, Any]],
        name: str,
        description: str,
        execution_mode: str
    ) -> Dict[str, Any]:
        """生成预览信息"""
        steps_preview: List[Dict[str, Any]] = []
        defined_vars: Set[str] = set()
        extracted_vars: Set[str] = set()

        if isinstance(config, YamlConfig):
            defined_vars.update(config.env_vars.keys())
            steps = config.steps
        else:
            if 'env_vars' in config and isinstance(config['env_vars'], dict):
                defined_vars.update(config['env_vars'].keys())
            steps = config.get('steps', [])

        for step_idx, step in enumerate(steps):
            step_info = {
                'order': step_idx,
                'name': step['name'],
                'method': step.get('request', {}).get('method', ''),
                'url': step.get('request', {}).get('url', ''),
                'assertions_count': len(step.get('assertions', [])),
                'extract_vars': []
            }

            for extract in step.get('extract', []):
                var_name = extract.get('name')
                if var_name:
                    step_info['extract_vars'].append(var_name)
                    extracted_vars.add(var_name)

            steps_preview.append(step_info)

        all_used_vars = self._collect_all_used_variables(steps)
        undefined_vars = all_used_vars - defined_vars - extracted_vars

        preview = {
            'name': name,
            'description': description,
            'execution_mode': execution_mode,
            'total_steps': len(steps),
            'steps_preview': steps_preview,
            'variables': {
                'defined': list(defined_vars),
                'extracted': list(extracted_vars),
                'undefined': list(undefined_vars) if undefined_vars else []
            }
        }
        return preview

    def _collect_all_used_variables(self, steps: List[Dict[str, Any]]) -> set[str]:
        """收集所有使用的变量"""
        import re
        used_vars: set[str] = set()

        for step_idx, step in enumerate(steps):
            request = step.get('request', {})
            base_location = f'steps[{step_idx}].request'

            if 'url' in request:
                self._collect_from_string(request['url'], f'{base_location}.url', used_vars, re)

            if 'headers' in request:
                for key, value in request['headers'].items():
                    self._collect_from_string(value, f'{base_location}.headers.{key}', used_vars, re)

            if 'body' in request:
                self._collect_from_object(request['body'], f'{base_location}.body', used_vars, re)

        return used_vars

    def _collect_from_string(self, text: str, location: str, variables: set[str], re_module: types.ModuleType) -> None:
        """从字符串收集变量"""
        if not isinstance(text, str):
            return  # type: ignore[unreachable]

        var_pattern = re_module.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_\.]*(\s*\|\s*default\s*:\s*"[^"]*")?\s*)}}')
        matches = var_pattern.findall(text)
        for match in matches if matches else []:
            var = match[0].strip()
            if '|' in var:
                var = var.split('|')[0].strip()
            # 提取根变量名
            root_var = var.split('.')[0]
            variables.add(root_var)

    def _collect_from_object(self, obj: Any, base_location: str, variables: set[str], re: types.ModuleType) -> None:
        """递归收集对象中的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f'{base_location}.{key}'
                if isinstance(value, str):
                    self._collect_from_string(value, location, variables, re)
                else:
                    self._collect_from_object(value, location, variables, re)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f'{base_location}[{idx}]'
                if isinstance(item, str):
                    self._collect_from_string(item, location, variables, re)
                else:
                    self._collect_from_object(item, location, variables, re)

    @transaction.atomic
    def _persist_to_database(
        self,
        config: Union[YamlConfig, Dict[str, Any]],
        name: str,
        description: str,
        execution_mode: str
    ) -> Dict[str, Any]:
        """持久化到数据库"""
        # 1. 创建 RequestCollection
        collection = RequestCollection.objects.create(
            name=name,
            description=description,
            execution_mode=execution_mode,
            project_id=self.project_id,
            created_by_id=self.created_by_id
        )

        # 2. 创建步骤
        steps = config.steps if isinstance(config, YamlConfig) else config.get('steps', [])
        for step_idx, step in enumerate(steps):
            self._create_step(collection, step, step_idx)

        result: Dict[str, Any] = {
            'collection_id': collection.id,
            'name': collection.name,
            'total_steps': len(steps),
            'total_api_requests': len(self.created_objects['api_requests']),
            'total_assertions': len(self.created_objects['assertions']),
            'created_at': collection.created_at.isoformat()
        }

        return result

    def _create_step(self, collection: RequestCollection, step: Dict[str, Any], step_idx: int) -> None:
        """创建单个步骤"""
        # 1. 创建 ApiRequest
        request_data = step.get('request', {})
        headers = request_data.get('headers') or {}
        body = request_data.get('body') or {}
        api_request = ApiRequest.objects.create(
            name=step['name'],
            url=request_data['url'],
            method=request_data['method'],
            headers=json.dumps(headers) if isinstance(headers, dict) else str(headers),
            body=json.dumps(body) if isinstance(body, dict) else str(body),
            project_id=self.project_id,
            created_by_id=self.created_by_id
        )

        # 2. 创建 CollectionRequest
        collection_request = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=step_idx,
            stop_on_failure=step.get('stop_on_failure', True),
            extract_rules=step.get('extract', []),
            request_count=step.get('request_count', 1)
        )

        # 3. 创建断言
        for assertion_idx, assertion in enumerate(step.get('assertions', [])):
            field = assertion.get('path', '') if assertion.get('type') == 'jsonpath' else assertion.get('field', '')
            api_assertion = ApiAssertion.objects.create(
                api_request=api_request,
                assertion_type=assertion['type'],
                field_path=field,
                comparison=assertion['comparison'],
                expected_value=str(assertion['expected'])
            )

    def validate_only(self, yaml_content: str) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """仅验证YAML，不转换"""
        is_valid, errors, warnings = self.validator.validate(yaml_content)

        preview: Optional[Dict[str, Any]] = None
        if is_valid:
            config = yaml.safe_load(yaml_content)
            preview = self._generate_preview(config, '验证中', '', 'chain')

        return is_valid, errors, warnings, preview
