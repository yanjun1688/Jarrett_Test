"""
测试脚本引擎 - 支持JSON/YAML格式的测试链路
支持变量提取、模板替换、setup/teardown
"""

from typing import Any, Dict, List, Optional
import yaml
import json
import re
from jsonpath_ng import parse as jsonpath_parse
import httpx
import json as json_lib
from datetime import datetime
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class TestChainExecutor:
    """测试链路执行器"""

    def __init__(self, base_context: Optional[Dict[str, Any]] = None) -> None:
        self.context = base_context or {}
        self.logs: List[str] = []
        self.session: Optional[httpx.Client] = None

    def log(self, message: str) -> None:
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Windows GBK 编码无法输出 emoji，替换为 ASCII 安全字符后再写日志
        safe_entry = log_entry.encode('ascii', errors='replace').decode('ascii')
        logger.info(safe_entry)

    
    

    def render_template(self, template: Any) -> Any:
        """
        渲染模板字符串，替换 {{variable}} 为实际值（使用统一模板引擎）

        支持：
        - 简单变量：{{var}}
        - 嵌套变量：{{user.name}}、{{data.0.id}}
        - 默认值：{{token|default:"abc"}}

        Args:
            template: 字符串或包含模板的对象

        Returns:
            渲染后的字符串或对象
        """
        from testmanager_app.utils.template_renderer import TemplateRenderer

        try:
            return TemplateRenderer.render(template, self.context, default_value="")
        except Exception as e:
            self.log(f"模板渲染失败: {str(e)}")
            return template

    def extract_variables(self, response: httpx.Response, extract_rules: List[Dict[str, Any]]) -> None:
        """
        从响应中提取变量

        Args:
            response: httpx.Response 对象
            extract_rules: 提取规则列表
                [
                    {
                        "name": "token",
                        "jsonpath": "$.data.token"
                    }
                ]
        """
        if not extract_rules:
            return

        try:
            response_json = response.json()
        except Exception as e:
            self.log(f"警告: 无法解析响应为JSON，跳过变量提取: {str(e)}")
            return

        for rule in extract_rules:
            try:
                name = rule['name']
                jsonpath_expr = rule['jsonpath']

                # 执行jsonpath查询
                expr = jsonpath_parse(jsonpath_expr)
                matches = [match.value for match in expr.find(response_json)]

                if matches:
                    value = matches[0]
                    self.context[name] = value
                    self.log(f"提取变量: {name} = {value}")
                else:
                    self.log(f"警告: jsonpath '{jsonpath_expr}' 未找到匹配值")

            except Exception as e:
                self.log(f"提取变量失败 '{name}': {str(e)}")

    def execute_request(self, request_data):
        """
        执行单个HTTP请求

        Args:
            request_data: 请求配置
                {
                    "method": "POST",
                    "url": "https://api.example.com/login",
                    "headers": {...},
                    "json": {...}
                }

        Returns:
            httpx.Response 对象
        """
        method = request_data.get('method', 'GET')
        url = request_data.get('url')
        headers = request_data.get('headers', {})

        # 渲染所有模板变量
        url = self.render_template(url)
        headers = self.render_template(headers)
        
        self.log(f"请求头: {json_lib.dumps(headers, ensure_ascii=False)}")

        # SSRF 防护：验证目标 URL
        from shared.utils.url_validator import validate_request_url
        url = validate_request_url(url)

        self.log(f"发送请求: {method} {url}")

        # 准备请求参数
        kwargs = {
            'method': method,
            'url': url,
            'headers': headers,
            'timeout': 30.0
        }

        # 处理不同类型的请求体
        if 'json' in request_data:
            json_data = self.render_template(request_data['json'])
            kwargs['json'] = json_data
            self.log(f"请求JSON数据: {json_lib.dumps(json_data, ensure_ascii=False)}")
        elif 'data' in request_data:
            kwargs['data'] = self.render_template(request_data['data'])
        elif 'content' in request_data:
            kwargs['content'] = self.render_template(request_data['content'])

        # 发送请求
        if not self.session:
            self.session = httpx.Client()

        response = self.session.request(**kwargs)
        return response

    def validate_assertions(self, response, assertions):
        """
        验证断言

        Args:
            response: httpx.Response 对象
            assertions: 断言列表
                [
                    {
                        "type": "status_code",
                        "expected": 200,
                        "comparison": "equals"
                    },
                    {
                        "type": "jsonpath",
                        "expression": "$.code",
                        "expected": 0,
                        "comparison": "equals"
                    }
                ]
        """
        if not assertions:
            return True, []

        all_passed = True
        results = []

        try:
            response_json = response.json()
        except (json.JSONDecodeError, ValueError):
            response_json = None

        for assertion in assertions:
            actual = None
            try:
                assertion_type = assertion.get('type')
                expected = assertion.get('expected')
                comparison = assertion.get('comparison', 'equals')

                if assertion_type == 'status_code':
                    actual = response.status_code
                    passed = self._compare(actual, expected, comparison)
                    self.log(f"断言[状态码]: 期望={expected}, 实际={actual}, 比较={comparison}, {'✅ 通过' if passed else '❌ 失败'}")

                elif assertion_type == 'jsonpath' and response_json:
                    jsonpath_expr = assertion.get('expression')
                    expr = jsonpath_parse(jsonpath_expr)
                    matches = [match.value for match in expr.find(response_json)]

                    if matches:
                        actual = matches[0]
                        passed = self._compare(actual, expected, comparison)
                        self.log(f"断言[JSONPath]: {jsonpath_expr}, 期望={expected}, 实际={actual}, 比较={comparison}, {'✅ 通过' if passed else '❌ 失败'}")
                    else:
                        passed = False
                        self.log(f"断言[JSONPath]: {jsonpath_expr}, 未找到值, ❌ 失败")

                else:
                    passed = False
                    self.log(f"断言[未知类型]: {assertion_type}, ❌ 失败")

                results.append({
                    'type': assertion_type,
                    'passed': passed,
                    'expected': expected,
                    'actual': actual,
                    'comparison': comparison,
                })

                if not passed:
                    all_passed = False

            except Exception as e:
                self.log(f"断言验证失败: {str(e)}")
                results.append({
                    'type': assertion.get('type'),
                    'passed': False,
                    'expected': assertion.get('expected'),
                    'actual': actual,
                    'error': str(e),
                })
                all_passed = False

        return all_passed, results

    @staticmethod
    def _compare(actual: Any, expected: Any, comparison: str) -> bool:
        """执行比较操作

        Args:
            actual: 实际值
            expected: 期望值
            comparison: 比较方式 (equals, not_equals, contains, gt, gte, lt, lte)

        Returns:
            比较结果
        """
        if comparison == 'equals':
            return bool(actual == expected)
        elif comparison == 'not_equals':
            return bool(actual != expected)
        elif comparison == 'contains':
            return str(expected) in str(actual)
        elif comparison in ('gt', 'greater_than'):
            if actual is not None and expected is not None:
                return float(actual) > float(expected)
            return False
        elif comparison in ('gte', 'greater_than_or_equal'):
            if actual is not None and expected is not None:
                return float(actual) >= float(expected)
            return False
        elif comparison in ('lt', 'less_than'):
            if actual is not None and expected is not None:
                return float(actual) < float(expected)
            return False
        elif comparison in ('lte', 'less_than_or_equal'):
            if actual is not None and expected is not None:
                return float(actual) <= float(expected)
            return False
        else:
            # 默认 equals
            return bool(actual == expected)

    def execute_step(self, step):
        """
        执行单个步骤

        Args:
            step: 步骤配置
                {
                    "name": "用户登录",
                    "request": {...},
                    "extract": [...],
                    "assertions": [...]
                }
        """
        step_name = step.get('name', '未命名步骤')
        self.log(f"======== 执行步骤: {step_name} ========")

        try:
            # 1. 执行请求
            request_data = step.get('request', {})
            response = self.execute_request(request_data)

            self.log(f"响应状态码: {response.status_code}")
            self.log(f"响应时间: {response.elapsed.total_seconds():.4f}秒")

            # 尝试解析响应体
            try:
                response_json = response.json()
                formatted_json = json_lib.dumps(response_json, indent=2, ensure_ascii=False)
                self.log(f"响应体:\n{formatted_json[:1000]}{'...' if len(formatted_json) > 1000 else ''}")
            except (json.JSONDecodeError, ValueError):
                self.log(f"响应体(文本): {response.text[:500]}")

            # 2. 提取变量
            extract_rules = step.get('extract', [])
            self.extract_variables(response, extract_rules)

            # 3. 验证断言
            assertions = step.get('assertions', [])
            passed, assertion_results = self.validate_assertions(response, assertions)

            if passed:
                self.log(f"✅ 步骤 '{step_name}' 通过")
            else:
                self.log(f"❌ 步骤 '{step_name}' 失败")

            try:
                response_json = response.json()
            except (json.JSONDecodeError, ValueError):
                response_json = None

            return {
                'success': passed,
                'status_code': response.status_code,
                'response_data': response_json,
                'elapsed': response.elapsed.total_seconds(),
                'assertion_results': assertion_results
            }

        except Exception as e:
            self.log(f"❌ 步骤 '{step_name}' 执行异常: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def execute_test_chain(self, script_content, script_format='yaml'):
        """
        执行完整的测试链路

        Args:
            script_content: YAML或JSON字符串
            script_format: 'yaml' 或 'json'

        Returns:
            {
                'success': bool,
                'logs': [str],
                'context': dict,
                'results': [dict]
            }
        """
        self.log(f"======== 开始执行测试链路 ========")
        self.log(f"脚本格式: {script_format.upper()}")

        try:
            # 1. 解析脚本
            if script_format.lower() == 'yaml':
                config = yaml.safe_load(script_content)
            elif script_format.lower() == 'json':
                config = json_lib.loads(script_content)
            else:
                raise ValueError(f"不支持的格式: {script_format}")

            self.log(f"测试名称: {config.get('name', '未命名')}")
            self.log(f"测试描述: {config.get('description', '无描述')}")

            # 2. 初始化上下文
            variables = config.get('variables', {})
            for var_name, var_value in variables.items():
                self.context[var_name] = var_value
                self.log(f"初始化变量: {var_name} = {var_value}")

            # 3. 执行setup
            setup_steps = config.get('setup', [])
            if setup_steps:
                self.log("======== 执行 Setup ========")
                for step in setup_steps:
                    result = self.execute_step(step)
                    if not result['success']:
                        self.log(f"❌ Setup失败，中止执行")
                        return {
                            'success': False,
                            'logs': self.logs,
                            'context': self.context,
                            'results': []
                        }

            # 4. 执行测试步骤
            test_steps = config.get('steps') or config.get('test_steps', [])
            results = []
            all_passed = True

            self.log("======== 执行测试步骤 ========")
            for step in test_steps:
                result = self.execute_step(step)
                results.append(result)

                if not result['success']:
                    all_passed = False
                    # 是否继续执行可由配置决定
                    if config.get('stop_on_failure', True):
                        self.log(f"步骤失败，中止执行")
                        break

            # 5. 执行teardown（无论测试结果如何都会执行）
            teardown_steps = config.get('teardown', [])
            if teardown_steps:
                self.log("======== 执行 Teardown ========")
                for step in teardown_steps:
                    try:
                        self.execute_step(step)
                    except Exception as e:
                        self.log(f"Teardown步骤执行出错: {str(e)}")

            self.log("======== 执行完成 ========")
            self.log(f"执行结果: {'✅ 通过' if all_passed else '❌ 失败'}")

            return {
                'success': all_passed,
                'logs': self.logs,
                'context': self.context,
                'results': results
            }

        except Exception as e:
            self.log(f"❌ 执行测试链路失败: {str(e)}")
            import traceback
            self.log(f"错误详情:\n{traceback.format_exc()}")

            return {
                'success': False,
                'logs': self.logs,
                'error': str(e),
                'context': self.context,
                'results': []
            }
        finally:
            if self.session:
                self.session.close()

    def execute_yaml_script(self, script_content):
        """执行YAML格式脚本"""
        return self.execute_test_chain(script_content, script_format='yaml')

    def execute_json_script(self, script_content):
        """执行JSON格式脚本"""
        return self.execute_test_chain(script_content, script_format='json')

    def execute_api_script(self, script_content):
        """执行API脚本（JSON格式）"""
        return self.execute_test_chain(script_content, script_format='json')

    
