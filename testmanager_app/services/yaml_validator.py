"""
YAML格式验证服务
用于验证YAML配置文件的语法和格式
"""

import re
import yaml
from typing import List, Dict, Any, Tuple
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError
from django.core.exceptions import ValidationError


class YamlValidator:
    """YAML配置文件验证器"""

    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
        self.variable_pattern = re.compile(r'{{\s*([a-zA-Z_][a-zA-Z0-9_\.]*(\s*\|\s*default\s*:\s*"[^"]*")?\s*)}}')

    def validate(self, yaml_content: str, check_variables: bool = True, check_jsonpath: bool = True) -> Tuple[bool, List[Dict], List[Dict]]:
        """
        验证YAML配置文件

        Args:
            yaml_content: YAML内容（字符串）
            check_variables: 是否检查变量语法
            check_jsonpath: 是否验证JSONPath表达式

        Returns:
            (is_valid, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []

        try:
            # 1. 验证YAML语法
            config = self._validate_yaml_syntax(yaml_content)
        except yaml.YAMLError as e:
            self.validation_errors.append({
                'level': 'error',
                'type': 'yaml_syntax',
                'message': f'YAML语法错误: {str(e)}',
                'location': 'root'
            })
            return False, self.validation_errors, self.validation_warnings

        # 2. 验证基础结构
        self._validate_basic_structure(config)

        # 3. 验证变量语法（如果需要）
        if check_variables:
            self._validate_variables(config)

        # 4. 验证JSONPath表达式（如果需要）
        if check_jsonpath and config.get('steps'):
            self._validate_jsonpath_expressions(config)

        # 5. 验证断言
        self._validate_assertions(config)

        is_valid = len([e for e in self.validation_errors if e['level'] == 'error']) == 0

        return is_valid, self.validation_errors, self.validation_warnings

    def _validate_yaml_syntax(self, yaml_content: str) -> Dict[Any, Any]:
        """验证YAML语法并返回解析后的配置"""
        return yaml.safe_load(yaml_content)

    def _validate_basic_structure(self, config: Dict) -> None:
        """验证基础结构"""
        # 检查必填字段
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in config:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': f'缺少必填字段: {field}',
                    'location': 'root'
                })

        # 检查steps是否为列表且非空
        if 'steps' in config:
            if not isinstance(config['steps'], list):
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'invalid_type',
                    'message': 'steps必须是列表类型',
                    'location': 'steps'
                })
            elif len(config['steps']) == 0:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'empty_list',
                    'message': 'steps列表不能为空',
                    'location': 'steps'
                })

        # 检查每个步骤的结构
        if config.get('steps'):
            for idx, step in enumerate(config['steps']):
                self._validate_step_structure(step, idx)

    def _validate_step_structure(self, step: Dict, step_index: int) -> None:
        """验证单个步骤的结构"""
        # 检查必填字段
        required_fields = ['name', 'request']
        for field in required_fields:
            if field not in step:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': f'缺少必填字段: {field}',
                    'location': f'steps[{step_index}]'
                })

        # 检查request结构
        if 'request' in step:
            request = step['request']
            if 'url' not in request:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': 'request缺少必填字段: url',
                    'location': f'steps[{step_index}].request'
                })
            if 'method' not in request:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': 'request缺少必填字段: method',
                    'location': f'steps[{step_index}].request'
                })

            # 验证method是否为有效HTTP方法
            valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
            if request.get('method') and request['method'].upper() not in valid_methods:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'invalid_value',
                    'message': f'无效的HTTP方法: {request["method"]}',
                    'location': f'steps[{step_index}].request.method'
                })

    def _validate_variables(self, config: Dict) -> None:
        """验证模板变量语法"""
        # 收集所有定义的环境变量
        defined_vars = set()
        if 'env_vars' in config and isinstance(config['env_vars'], dict):
            defined_vars.update(config['env_vars'].keys())

        # 检查steps中的变量使用
        if config.get('steps'):
            for step_idx, step in enumerate(config['steps']):
                self._check_variables_in_step(step, step_idx, defined_vars)

        # 提示未定义变量使用
        undefined_vars = self._extract_undefined_variables(config)
        for var, locations in undefined_vars.items():
            # 第一个使用位置作为警告位置
            first_location = locations[0]
            self.validation_warnings.append({
                'level': 'warning',
                'type': 'undefined_variable',
                'message': f'变量 {var} 未在 env_vars 中定义',
                'location': first_location
            })

    def _check_variables_in_step(self, step: Dict, step_idx: int, defined_vars: set) -> None:
        """检查步骤中的变量"""
        request = step.get('request', {})

        # 检查URL
        if 'url' in request:
            self._check_variables_in_string(
                request['url'],
                f'steps[{step_idx}].request.url',
                defined_vars
            )

        # 检查headers
        if 'headers' in request:
            for key, value in request['headers'].items():
                self._check_variables_in_string(
                    value,
                    f'steps[{step_idx}].request.headers.{key}',
                    defined_vars
                )

        # 检查body（递归）
        if 'body' in request:
            self._scan_for_variables(request['body'], f'steps[{step_idx}].request.body', defined_vars)

        # 检查断言中的期望值
        for assertion_idx, assertion in enumerate(step.get('assertions', [])):
            if 'expected' in assertion:
                expected = assertion['expected']
                location = f'steps[{step_idx}].assertions[{assertion_idx}].expected'
                if isinstance(expected, str):
                    self._check_variables_in_string(expected, location, defined_vars)

    def _check_variables_in_string(self, text: str, location: str, defined_vars: set) -> None:
        """检查字符串中的变量语法"""
        if not isinstance(text, str):
            return

        if '{{' in text:
            # 检查是否匹配
            if '}}' not in text:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'unmatched_braces',
                    'message': '变量语法错误: {{ 缺少对应的 }}',
                    'location': location
                })
            else:
                # 验证每个变量
                variables = self._extract_variables_from_string(text)
                for var in variables:
                    var_name = var.strip()

                    # 过滤默认值语法
                    if '|' in var_name:
                        var_name = var_name.split('|')[0].strip()

                    # 验证变量名格式
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_\.]*$', var_name):
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_variable_name',
                            'message': f'无效的变量名: {var_name}',
                            'location': location
                        })

                    # 检查嵌套路径
                    if '.' in var_name:
                        parts = var_name.split('.')
                        if any(not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part) for part in parts):
                            self.validation_errors.append({
                                'level': 'error',
                                'type': 'invalid_variable_path',
                                'message': f'无效的变量路径: {var_name}',
                                'location': location
                            })

    def _scan_for_variables(self, obj: Any, base_location: str, defined_vars: set) -> None:
        """递归扫描对象中的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f"{base_location}.{key}"
                if isinstance(value, str):
                    self._check_variables_in_string(value, location, defined_vars)
                else:
                    self._scan_for_variables(value, location, defined_vars)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f"{base_location}[{idx}]"
                if isinstance(item, str):
                    self._check_variables_in_string(item, location, defined_vars)
                else:
                    self._scan_for_variables(item, location, defined_vars)

    def _extract_variables_from_string(self, text: str) -> List[str]:
        """从字符串中提取所有变量"""
        matches = self.variable_pattern.findall(text)
        return [match[0] for match in matches] if matches else []

    def _extract_undefined_variables(self, config: Dict) -> Dict[str, List[str]]:
        """提取未定义的变量"""
        # 收集所有定义的变量
        defined_vars = set()
        if 'env_vars' in config and isinstance(config['env_vars'], dict):
            defined_vars.update(config['env_vars'].keys())

        # 提取所有使用的变量
        used_vars = {}
        self._collect_used_variables(config, used_vars)

        # 找出未定义的变量
        undefined_vars = {}
        for var, locations in used_vars.items():
            if var not in defined_vars:
                undefined_vars[var] = locations

        return undefined_vars

    def _collect_used_variables(self, obj: Any, variables: Dict[str, List[str]], base_location: str = 'root') -> None:
        """收集所有使用的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f"{base_location}.{key}"
                if isinstance(value, str):
                    self._collect_from_string(value, location, variables)
                elif key == 'expected' and 'assertions' not in base_location:
                    # 跳过断言中的expected，因为它们不需要预定义
                    continue
                else:
                    self._collect_used_variables(value, variables, location)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f"{base_location}[{idx}]"
                if isinstance(item, str):
                    self._collect_from_string(item, location, variables)
                else:
                    self._collect_used_variables(item, variables, location)

    def _collect_from_string(self, text: str, location: str, variables: Dict[str, List[str]]) -> None:
        """从字符串收集变量"""
        if not isinstance(text, str):
            return

        for var in self._extract_variables_from_string(text):
            var_name = var.strip()
            if '|' in var_name:
                var_name = var_name.split('|')[0].strip()

            # 将user.name转换为user（最外层变量）
            root_var = var_name.split('.')[0]
            if root_var not in variables:
                variables[root_var] = []
            variables[root_var].append(location)

    def _validate_jsonpath_expressions(self, config: Dict) -> None:
        """验证JSONPath表达式"""
        for step_idx, step in enumerate(config['steps']):
            # 验证extract规则
            for extract_idx, extract in enumerate(step.get('extract', [])):
                if 'path' in extract:
                    try:
                        parse(extract['path'])
                    except JsonPathParserError as e:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_jsonpath',
                            'message': f'无效的JSONPath表达式: {extract["path"]} - {str(e)}',
                            'location': f'steps[{step_idx}].extract[{extract_idx}].path'
                        })

            # 验证assertion中的path
            for assertion_idx, assertion in enumerate(step.get('assertions', [])):
                if assertion.get('type') == 'jsonpath':
                    if 'path' not in assertion:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'missing_field',
                            'message': 'JSONPath断言缺少必填字段: path',
                            'location': f'steps[{step_idx}].assertions[{assertion_idx}]'
                        })
                    else:
                        try:
                            parse(assertion['path'])
                        except JsonPathParserError as e:
                            self.validation_errors.append({
                                'level': 'error',
                                'type': 'invalid_jsonpath',
                                'message': f'无效的JSONPath表达式: {assertion["path"]} - {str(e)}',
                                'location': f'steps[{step_idx}].assertions[{assertion_idx}].path'
                            })

    def _validate_assertions(self, config: Dict) -> None:
        """验证断言配置"""
        valid_comparison_types = ['equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte']

        for step_idx, step in enumerate(config.get('steps', [])):
            for assertion_idx, assertion in enumerate(step.get('assertions', [])):
                # 验证必填字段
                required_fields = ['type', 'expected', 'comparison']
                for field in required_fields:
                    if field not in assertion:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'missing_field',
                            'message': f'断言缺少必填字段: {field}',
                            'location': f'steps[{step_idx}].assertions[{assertion_idx}]'
                        })

                # 验证type枚举值
                if 'type' in assertion:
                    if assertion['type'] not in ['status_code', 'jsonpath']:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_value',
                            'message': f'断言类型不合法: {assertion["type"]}，必须为 status_code 或 jsonpath',
                            'location': f'steps[{step_idx}].assertions[{assertion_idx}].type'
                        })

                # 验证comparison枚举值
                if 'comparison' in assertion:
                    if assertion['comparison'] not in valid_comparison_types:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_value',
                            'message': f'比较方式不合法: {assertion["comparison"]}',
                            'location': f'steps[{step_idx}].assertions[{assertion_idx}].comparison'
                        })

                # type为jsonpath时需要path字段
                if assertion.get('type') == 'jsonpath' and 'path' not in assertion:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': 'JSONPath断言缺少必填字段: path',
                        'location': f'steps[{step_idx}].assertions[{assertion_idx}]'
                    })

                # type为status_code时验证expected是否为整数
                if assertion.get('type') == 'status_code':
                    if 'expected' in assertion and not str(assertion['expected']).isdigit():
                        self.validation_errors.append({
                            'level': 'warning',
                            'type': 'type_mismatch',
                            'message': '状态码断言的expected应为整数',
                            'location': f'steps[{step_idx}].assertions[{assertion_idx}].expected'
                        })
