"""
YAML到RequestCollection的转换服务
将YAML配置文件转换为数据库中的RequestCollection及相关模型
"""

import yaml
import base64
from typing import Dict, Any, List, Tuple
from django.db import transaction
from django.contrib.auth.models import User
from ..models import (
    RequestCollection,
    ApiRequest,
    CollectionRequest,
    ApiAssertion,
    Project
)
from .yaml_validator import YamlValidator


class YamlToCollectionConverter:
    """YAML到RequestCollection的转换器"""

    def __init__(self, project_id: int, created_by_id: int):
        self.project_id = project_id
        self.created_by_id = created_by_id
        self.validator = YamlValidator()
        self.created_objects = {
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
            # 1. 验证YAML
            print(f"[DEBUG] 开始验证YAML格式...")
            is_valid, errors, warnings = self.validator.validate(yaml_content)
            print(f"[DEBUG] 验证结果: is_valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}")

            if not is_valid:
                error_messages = '\n'.join([e['message'] for e in errors if e['level'] == 'error'])
                print(f"[DEBUG] 验证失败: {error_messages}")
                return False, {
                    'error': 'YAML验证失败',
                    'errors': errors,
                    'warnings': warnings
                }

            # 2. 解析YAML
            print(f"[DEBUG] 解析YAML内容...")
            config = yaml.safe_load(yaml_content)
            print(f"[DEBUG] YAML解析成功: name={config.get('name')}, steps数量={len(config.get('steps', []))}")

            # 3. 生成预览（先于保存）
            preview = self._generate_preview(config, name, description, execution_mode)

            # 4. 如果只是验证，返回预览
            if validate_only:
                print(f"[DEBUG] 验证模式，返回预览...")
                return True, {
                    'valid': True,
                    'preview': preview,
                    'validation_result': {
                        'is_valid': True,
                        'errors': errors,
                        'warnings': warnings
                    }
                }

            # 5. 保存到数据库
            print(f"[DEBUG] 开始保存到数据库...")
            result = self._persist_to_database(config, name, description, execution_mode)
            print(f"[DEBUG] 保存成功, collection_id={result['collection_id']}")

            return True, result

        except Exception as e:
            print(f"[ERROR] 转换失败: {str(e)}")
            import traceback
            print(f"[ERROR] 详细错误: {traceback.format_exc()}")
            return False, {
                'error': f'转换失败: {str(e)}',
                'detail': traceback.format_exc()
            }

    def convert_from_base64(self, base64_content: str, name: str, description: str = '',
                           execution_mode: str = 'chain', validate_only: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """从Base64编码的YAML内容转换"""
        print(f"[DEBUG] Base64解码...")
        try:
            yaml_content = base64.b64decode(base64_content.encode('utf-8')).decode('utf-8')
            print(f"[DEBUG] Base64解码成功，内容长度: {len(yaml_content)}")
            return self.convert(yaml_content, name, description, execution_mode, validate_only)
        except Exception as e:
            print(f"[ERROR] Base64解码失败: {str(e)}")
            return False, {'error': f'Base64解码失败: {str(e)}'}

    def _generate_preview(self, config: Dict, name: str, description: str, execution_mode: str) -> Dict[str, Any]:
        """生成预览信息"""
        print(f"[DEBUG] 生成预览信息...")
        steps_preview = []
        defined_vars = set()
        extracted_vars = set()

        # 收集定义的变量
        if 'env_vars' in config and isinstance(config['env_vars'], dict):
            defined_vars.update(config['env_vars'].keys())

        # 收集提取的变量
        for step_idx, step in enumerate(config.get('steps', [])):
            step_info = {
                'order': step_idx,
                'name': step['name'],
                'method': step.get('request', {}).get('method', ''),
                'url': step.get('request', {}).get('url', ''),
                'assertions_count': len(step.get('assertions', [])),
                'extract_vars': []
            }

            # 收集提取的变量
            for extract in step.get('extract', []):
                var_name = extract.get('name')
                if var_name:
                    step_info['extract_vars'].append(var_name)
                    extracted_vars.add(var_name)

            steps_preview.append(step_info)

        # 收集所有使用的变量
        all_used_vars = self._collect_all_used_variables(config)
        undefined_vars = all_used_vars - defined_vars - extracted_vars

        preview = {
            'name': name,
            'description': description,
            'execution_mode': execution_mode,
            'total_steps': len(config.get('steps', [])),
            'steps_preview': steps_preview,
            'variables': {
                'defined': list(defined_vars),
                'extracted': list(extracted_vars),
                'undefined': list(undefined_vars) if undefined_vars else []
            }
        }

        print(f"[DEBUG] 预览信息: total_steps={preview['total_steps']}, vars={preview['variables']}")
        return preview

    def _collect_all_used_variables(self, config: Dict) -> set:
        """收集所有使用的变量"""
        used_vars = set()

        # 遍历steps收集变量使用（跳过断言中的expected）
        for step_idx, step in enumerate(config.get('steps', [])):
            request = step.get('request', {})
            base_location = f'steps[{step_idx}].request'

            # 收集URL中的变量
            if 'url' in request:
                self._collect_from_string(request['url'], f'{base_location}.url', used_vars)

            # 收集headers中的变量
            if 'headers' in request:
                for key, value in request['headers'].items():
                    self._collect_from_string(value, f'{base_location}.headers.{key}', used_vars)

            # 收集body中的变量
            if 'body' in request:
                self._collect_from_object(request['body'], f'{base_location}.body', used_vars)

            # 注意: 跳过断言中的expected，因为它们不需要预定义

        return used_vars

    def _collect_from_string(self, text: str, location: str, variables: set) -> None:
        """从字符串收集变量"""
        if not isinstance(text, str):
            return

        var_pattern = re.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_\.]*(\s*\|\s*default\s*:\s*"[^"]*")?\s*)}}')
        matches = var_pattern.findall(text)
        for match in matches if matches else []:
            var = match[0].strip()
            if '|' in var:
                var = var.split('|')[0].strip()
            # 提取根变量名
            root_var = var.split('.')[0]
            variables.add(root_var)

    def _collect_from_object(self, obj: Any, base_location: str, variables: set) -> None:
        """递归收集对象中的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f'{base_location}.{key}'
                if isinstance(value, str):
                    self._collect_from_string(value, location, variables)
                else:
                    self._collect_from_object(value, location, variables)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f'{base_location}[{idx}]'
                if isinstance(item, str):
                    self._collect_from_string(item, location, variables)
                else:
                    self._collect_from_object(item, location, variables)

    @transaction.atomic
    def _persist_to_database(self, config: Dict, name: str, description: str, execution_mode: str) -> Dict[str, Any]:
        """持久化到数据库"""
        print(f'[DEBUG] 开始数据库事务，创建集合...')
        # 1. 创建 RequestCollection
        collection = RequestCollection.objects.create(
            name=name,
            description=description,
            execution_mode=execution_mode,
            project_id=self.project_id,
            created_by_id=self.created_by_id
        )
        print(f'[DEBUG] 创建集合成功, id={collection.id}')

        # 2. 创建步骤
        for step_idx, step in enumerate(config['steps']):
            self._create_step(collection, step, step_idx)

        result = {
            'collection_id': collection.id,
            'name': collection.name,
            'total_steps': len(config['steps']),
            'total_api_requests': len(self.created_objects['api_requests']),
            'total_assertions': len(self.created_objects['assertions']),
            'created_at': collection.created_at.isoformat()
        }

        return result

    def _create_step(self, collection: RequestCollection, step: Dict, step_idx: int) -> None:
        """创建单个步骤"""
        print(f'[DEBUG] 创建步骤 {step_idx}: {step["name"]}')
        # 1. 创建 ApiRequest
        request_data = step.get('request', {})
        api_request = ApiRequest.objects.create(
            name=step['name'],
            url=request_data['url'],
            method=request_data['method'],
            headers=request_data.get('headers') or {},
            body=request_data.get('body') or {},
            project_id=self.project_id,
            created_by_id=self.created_by_id
        )
        print(f'[DEBUG] 创建ApiRequest成功, id={api_request.id}')

        # 2. 创建 CollectionRequest
        collection_request = CollectionRequest.objects.create(
            collection=collection,
            api_request=api_request,
            order_index=step_idx,
            stop_on_failure=step.get('stop_on_failure', True),
            extract_rules=step.get('extract', []),
            request_count=step.get('request_count', 1)
        )
        print(f'[DEBUG] 创建CollectionRequest成功, id={collection_request.id}')

        # 3. 创建断言
        for assertion_idx, assertion in enumerate(step.get('assertions', [])):
            field = assertion.get('path', '') if assertion.get('type') == 'jsonpath' else assertion.get('field', '')
            try:
                api_assertion = ApiAssertion.objects.create(
                    api_request=api_request,
                    assertion_type=assertion['type'],
                    field=field,
                    comparison=assertion['comparison'],
                    expected_value=str(assertion['expected'])
                )
                print(f'[DEBUG] 创建断言 {assertion_idx}: {api_assertion.assertion_type}')
            except Exception as e:
                print(f'[DEBUG] 创建断言失败: {str(e)}')
                raise

    def validate_only(self, yaml_content: str) -> Tuple[bool, List[Dict], List[Dict], Dict[str, Any]]:
        """仅验证YAML，不转换"""
        is_valid, errors, warnings = self.validator.validate(yaml_content)

        preview = None
        if is_valid:
            config = yaml.safe_load(yaml_content)
            preview = self._generate_preview(config, '验证中', '', 'chain')

        return is_valid, errors, warnings, preview
