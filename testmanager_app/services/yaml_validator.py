"""
YAML格式验证服务
用于验证YAML配置文件的语法和格式

验证规则与 ScriptEngine (script_engine.py) 执行引擎保持一致。
"""

from __future__ import annotations

import re
import yaml
from typing import List, Dict, Any, Tuple
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError
from django.core.exceptions import ValidationError


class YamlValidator:
    """YAML配置文件验证器

    验证规则以 ScriptEngine 执行引擎为权威源，确保验证通过的 YAML 可以被执行。
    """

    def __init__(self) -> None:
        self.validation_errors: List[Dict[str, Any]] = []
        self.validation_warnings: List[Dict[str, Any]] = []
        self.variable_pattern = re.compile(r'{{\s*(.*?)\s*}}')
        self.valid_var_pattern = re.compile(
            r'^[a-zA-Z_][a-zA-Z0-9_\.]*(\s*\|\s*default\s*:\s*"[^"]*")?$'
        )

    def validate(
        self,
        yaml_content: str,
        check_variables: bool = True,
        check_jsonpath: bool = True,
    ) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
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
            config = self._validate_yaml_syntax(yaml_content)
        except yaml.YAMLError as e:
            self.validation_errors.append({
                'level': 'error',
                'type': 'yaml_syntax',
                'message': f'YAML语法错误: {str(e)}',
                'location': 'root',
            })
            return False, self.validation_errors, self.validation_warnings

        self._validate_basic_structure(config)

        if check_variables:
            self._validate_variables(config)

        if check_jsonpath and config.get('steps'):
            self._validate_jsonpath_expressions(config)

        self._validate_assertions(config)

        is_valid = len([e for e in self.validation_errors if e['level'] == 'error']) == 0
        return is_valid, self.validation_errors, self.validation_warnings

    def _validate_yaml_syntax(self, yaml_content: str) -> Dict[str, Any]:
        """验证YAML语法并返回解析后的配置"""
        result: Dict[str, Any] = yaml.safe_load(yaml_content)
        return result

    def _validate_basic_structure(self, config: Dict[str, Any]) -> None:
        """验证基础结构（与 ScriptEngine.execute_test_chain 对齐）"""
        required_fields = ['name', 'steps']
        for field in required_fields:
            if field not in config:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': f'缺少必填字段: {field}',
                    'location': 'root',
                })

        if 'steps' in config:
            if not isinstance(config['steps'], list):
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'invalid_type',
                    'message': 'steps必须是列表类型',
                    'location': 'steps',
                })
            elif len(config['steps']) == 0:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'empty_list',
                    'message': 'steps列表不能为空',
                    'location': 'steps',
                })
            else:
                for idx, step in enumerate(config['steps']):
                    if isinstance(step, dict):
                        self._validate_step_structure(step, idx)
                    else:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_type',
                            'message': f'steps[{idx}]必须是字典类型',
                            'location': f'steps[{idx}]',
                        })

        # 验证可选的 setup / teardown 结构
        for section in ('setup', 'teardown'):
            if section in config:
                if not isinstance(config[section], list):
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'invalid_type',
                        'message': f'{section}必须是列表类型',
                        'location': section,
                    })
                else:
                    for idx, step in enumerate(config[section]):
                        if isinstance(step, dict):
                            self._validate_step_structure(step, idx, section=section)

        # 验证可选的 variables 结构
        if 'variables' in config and not isinstance(config['variables'], dict):
            self.validation_errors.append({
                'level': 'error',
                'type': 'invalid_type',
                'message': 'variables必须是字典类型',
                'location': 'variables',
            })

    def _validate_step_structure(
        self, step: Dict[str, Any], step_index: int, section: str = 'steps',
    ) -> None:
        """验证单个步骤的结构（与 ScriptEngine.execute_step 对齐）"""
        loc = f'{section}[{step_index}]'

        # 必填字段: name, request
        required_fields = ['name', 'request']
        for field in required_fields:
            if field not in step:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'missing_field',
                    'message': f'缺少必填字段: {field}',
                    'location': loc,
                })

        # 验证 request 结构
        if 'request' in step:
            request = step['request']
            if not isinstance(request, dict):
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'invalid_type',
                    'message': 'request必须是字典类型',
                    'location': f'{loc}.request',
                })
            else:
                if 'url' not in request:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': 'request缺少必填字段: url',
                        'location': f'{loc}.request',
                    })
                if 'method' not in request:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': 'request缺少必填字段: method',
                        'location': f'{loc}.request',
                    })

                valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
                method = request.get('method')
                if method and str(method).upper() not in valid_methods:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'invalid_value',
                        'message': f'无效的HTTP方法: {method}',
                        'location': f'{loc}.request.method',
                    })

        # 验证 extract 结构（ScriptEngine 要求 name + jsonpath）
        if 'extract' in step:
            extracts = step['extract']
            if not isinstance(extracts, list):
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'invalid_type',
                    'message': 'extract必须是列表类型',
                    'location': f'{loc}.extract',
                })
            else:
                for ext_idx, ext in enumerate(extracts):
                    if not isinstance(ext, dict):
                        continue
                    if 'name' not in ext:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'missing_field',
                            'message': 'extract规则缺少必填字段: name',
                            'location': f'{loc}.extract[{ext_idx}]',
                        })
                    if 'jsonpath' not in ext:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'missing_field',
                            'message': 'extract规则缺少必填字段: jsonpath',
                            'location': f'{loc}.extract[{ext_idx}]',
                        })

    # ------------------------------------------------------------------
    # 变量验证
    # ------------------------------------------------------------------

    def _validate_variables(self, config: Dict[str, Any]) -> None:
        """验证模板变量语法"""
        defined_vars: set[str] = set()
        if 'variables' in config and isinstance(config['variables'], dict):
            defined_vars.update(config['variables'].keys())

        if config.get('steps'):
            for step_idx, step in enumerate(config['steps']):
                if isinstance(step, dict):
                    self._check_variables_in_step(step, step_idx, defined_vars)

        undefined_vars = self._extract_undefined_variables(config)
        for var, locations in undefined_vars.items():
            first_location = locations[0]
            self.validation_warnings.append({
                'level': 'warning',
                'type': 'undefined_variable',
                'message': f'变量 {var} 未在 variables 中定义（可能由 extract 动态提取）',
                'location': first_location,
            })

    def _check_variables_in_step(
        self, step: Dict[str, Any], step_idx: int, defined_vars: set[str],
    ) -> None:
        """检查步骤中的变量"""
        request = step.get('request', {})
        if not isinstance(request, dict):
            return

        if 'url' in request:
            self._check_variables_in_string(
                request['url'], f'steps[{step_idx}].request.url', defined_vars,
            )

        if 'headers' in request and isinstance(request['headers'], dict):
            for key, value in request['headers'].items():
                if isinstance(value, str):
                    self._check_variables_in_string(
                        value, f'steps[{step_idx}].request.headers.{key}', defined_vars,
                    )

        # 请求体: json / data / content
        for body_key in ('json', 'data', 'content'):
            if body_key in request:
                self._scan_for_variables(
                    request[body_key], f'steps[{step_idx}].request.{body_key}', defined_vars,
                )

    def _check_variables_in_string(
        self, text: str, location: str, defined_vars: set[str],
    ) -> None:
        """检查字符串中的变量语法"""
        if not isinstance(text, str):
            return

        if '{{' in text:
            if '}}' not in text:
                self.validation_errors.append({
                    'level': 'error',
                    'type': 'unmatched_braces',
                    'message': '变量语法错误: {{ 缺少对应的 }}',
                    'location': location,
                })
            else:
                variables = self._extract_variables_from_string(text)
                for var in variables:
                    var_content = var.strip()
                    if not self.valid_var_pattern.match(var_content):
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_variable_name',
                            'message': f'无效的变量名: {var_content}',
                            'location': location,
                        })

    def _scan_for_variables(
        self, obj: Any, base_location: str, defined_vars: set[str],
    ) -> None:
        """递归扫描对象中的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f'{base_location}.{key}'
                if isinstance(value, str):
                    self._check_variables_in_string(value, location, defined_vars)
                else:
                    self._scan_for_variables(value, location, defined_vars)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f'{base_location}[{idx}]'
                if isinstance(item, str):
                    self._check_variables_in_string(item, location, defined_vars)
                else:
                    self._scan_for_variables(item, location, defined_vars)

    def _extract_variables_from_string(self, text: str) -> List[str]:
        """从字符串中提取所有变量"""
        matches = self.variable_pattern.findall(text)
        return matches if matches else []

    def _extract_undefined_variables(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取未定义的变量"""
        defined_vars: set[str] = set()
        if 'variables' in config and isinstance(config['variables'], dict):
            defined_vars.update(config['variables'].keys())

        used_vars: dict[str, list[str]] = {}
        self._collect_used_variables(config, used_vars)

        undefined_vars: Dict[str, List[str]] = {}
        for var, locations in used_vars.items():
            if var not in defined_vars:
                undefined_vars[var] = locations
        return undefined_vars

    def _collect_used_variables(
        self, obj: Any, variables: Dict[str, List[str]], base_location: str = 'root',
    ) -> None:
        """收集所有使用的变量"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                location = f'{base_location}.{key}'
                if isinstance(value, str):
                    self._collect_from_string(value, location, variables)
                else:
                    self._collect_used_variables(value, variables, location)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                location = f'{base_location}[{idx}]'
                if isinstance(item, str):
                    self._collect_from_string(item, location, variables)
                else:
                    self._collect_used_variables(item, variables, location)

    def _collect_from_string(
        self, text: str, location: str, variables: Dict[str, List[str]],
    ) -> None:
        """从字符串收集变量"""
        if not isinstance(text, str):
            return

        for var in self._extract_variables_from_string(text):
            var_name = var.strip()
            if '|' in var_name:
                var_name = var_name.split('|')[0].strip()
            root_var = var_name.split('.')[0]
            if root_var not in variables:
                variables[root_var] = []
            variables[root_var].append(location)

    # ------------------------------------------------------------------
    # JSONPath 验证
    # ------------------------------------------------------------------

    def _validate_jsonpath_expressions(self, config: Dict[str, Any]) -> None:
        """验证JSONPath表达式"""
        steps = config.get('steps', [])
        if not isinstance(steps, list):
            return

        for step_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue

            # 验证 extract 规则中的 jsonpath
            for ext_idx, ext in enumerate(step.get('extract', [])):
                if not isinstance(ext, dict):
                    continue
                if 'jsonpath' in ext:
                    try:
                        parse(ext['jsonpath'])
                    except JsonPathParserError as e:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'invalid_jsonpath',
                            'message': f'无效的JSONPath表达式: {ext["jsonpath"]} - {str(e)}',
                            'location': f'steps[{step_idx}].extract[{ext_idx}].jsonpath',
                        })

            # 验证 assertion 中的 expression（type=jsonpath 时）
            for a_idx, assertion in enumerate(step.get('assertions', [])):
                if not isinstance(assertion, dict):
                    continue
                if assertion.get('type') == 'jsonpath':
                    expr = assertion.get('expression')
                    if not expr:
                        self.validation_errors.append({
                            'level': 'error',
                            'type': 'missing_field',
                            'message': 'JSONPath断言缺少必填字段: expression',
                            'location': f'steps[{step_idx}].assertions[{a_idx}]',
                        })
                    else:
                        try:
                            parse(expr)
                        except JsonPathParserError as e:
                            self.validation_errors.append({
                                'level': 'error',
                                'type': 'invalid_jsonpath',
                                'message': f'无效的JSONPath表达式: {expr} - {str(e)}',
                                'location': f'steps[{step_idx}].assertions[{a_idx}].expression',
                            })

    # ------------------------------------------------------------------
    # 断言验证
    # ------------------------------------------------------------------

    def _validate_assertions(self, config: Dict[str, Any]) -> None:
        """验证断言配置（与 ScriptEngine.validate_assertions 对齐）

        执行引擎支持的断言类型: status_code, jsonpath
        执行引擎使用的字段: type, expected, comparison, expression(jsonpath时)
        comparison 支持: equals, not_equals, contains, gt, gte, lt, lte
        """
        valid_assertion_types = ['status_code', 'jsonpath']
        valid_comparison_types = ['equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte']

        steps = config.get('steps', [])
        if not isinstance(steps, list):
            return

        for step_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            for a_idx, assertion in enumerate(step.get('assertions', [])):
                if not isinstance(assertion, dict):
                    continue
                loc = f'steps[{step_idx}].assertions[{a_idx}]'

                # type 必填
                if 'type' not in assertion:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': '断言缺少必填字段: type',
                        'location': loc,
                    })
                    continue

                a_type = assertion['type']
                if a_type not in valid_assertion_types:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'invalid_value',
                        'message': f'断言类型不合法: {a_type}，必须为 status_code 或 jsonpath',
                        'location': f'{loc}.type',
                    })

                # expected 必填
                if 'expected' not in assertion:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': '断言缺少必填字段: expected',
                        'location': loc,
                    })

                # comparison 必填
                if 'comparison' not in assertion:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': '断言缺少必填字段: comparison',
                        'location': loc,
                    })
                elif assertion['comparison'] not in valid_comparison_types:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'invalid_value',
                        'message': f'比较方式不合法: {assertion["comparison"]}，'
                                   f'必须为 {", ".join(valid_comparison_types)} 之一',
                        'location': f'{loc}.comparison',
                    })

                # type=jsonpath 时 expression 必填
                if a_type == 'jsonpath' and 'expression' not in assertion:
                    self.validation_errors.append({
                        'level': 'error',
                        'type': 'missing_field',
                        'message': 'JSONPath断言缺少必填字段: expression',
                        'location': loc,
                    })

                # type=status_code 时 expected 应为整数
                if a_type == 'status_code' and 'expected' in assertion:
                    if not isinstance(assertion['expected'], int):
                        self.validation_warnings.append({
                            'level': 'warning',
                            'type': 'type_mismatch',
                            'message': '状态码断言的expected建议为整数类型',
                            'location': f'{loc}.expected',
                        })
