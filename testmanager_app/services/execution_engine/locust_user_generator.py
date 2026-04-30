"""
Locust 用户生成器
将 scenario JSON 动态转换为 HttpUser 子类（in-process，不写临时文件）

设计原则：
- 类型（type）元类方式创建，不走文件 IO
- 支持 api_request_id（引用已有）和 url/method（直接定义）双模式
- 变量提取（JSONPath/Regex/Header）和模板渲染（${variable}）
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

class TransactionContext:
    """事务上下文，步骤间通过 ${variable} 传递数据"""

    def __init__(self) -> None:
        self.variables: Dict[str, Any] = {}

    def set(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self.variables.get(name, default)

    def render(self, template: str) -> str:
        if not template:
            return template
        result = template
        for name, value in self.variables.items():
            placeholder = f'${{{name}}}'
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def render_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            return data
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.render(value)
            elif isinstance(value, dict):
                result[key] = self.render_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.render(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


def extract_value(response: Any, extractor: Dict[str, Any]) -> Any:
    """
    从 HTTP 响应中提取数据

    支持的提取器类型:
    - json_path: JSONPath 表达式
    - regex: 正则表达式
    - header: 响应头
    - status_code: HTTP 状态码
    - xpath: XPath 表达式
    """
    ext_type = extractor.get('type', '')
    expression = extractor.get('expression', '')

    if ext_type == 'json_path':
        try:
            from jsonpath_ng import parse as jsonpath_parse
            json_data = response.json()
            jsonpath_expr = jsonpath_parse(expression)
            matches = [match.value for match in jsonpath_expr.find(json_data)]
            return matches[0] if matches else None
        except Exception:
            return None

    elif ext_type == 'regex':
        match = re.search(expression, response.text)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
        return None

    elif ext_type == 'header':
        return response.headers.get(expression)

    elif ext_type == 'status_code':
        return response.status_code

    elif ext_type == 'xpath':
        try:
            from lxml import html
            tree = html.fromstring(response.content)
            result = tree.xpath(expression)
            return result[0] if result else None
        except Exception:
            return None

    return None


class DynamicUserBuilder:
    """
    将 scenario 配置转换为 Locust HttpUser 子类

    用法:
        builder = DynamicUserBuilder(scenario, host='http://localhost:8080')
        UserClass = builder.build()          # 返回 type
        user_classes = builder.build_all()    # 返回 [type]
    """

    def __init__(self, scenario: Dict[str, Any], host: str = '') -> None:
        self.scenario = scenario
        self.host = host
        self._api_requests: Dict[int, Any] = {}

    def _load_api_requests(self, steps: List[Dict[str, Any]]) -> None:
        """预加载步骤中引用的所有 ApiRequest，减少 DB 查询"""
        from testmanager_app.models import ApiRequest

        ids = []
        for step in steps:
            api_id = step.get('api_request_id')
            if api_id is not None:
                ids.append(int(api_id))

        if not ids:
            return

        for req in ApiRequest.objects.filter(id__in=ids):
            self._api_requests[req.id] = req

    def build(self) -> type:
        import sys
        print('[DEBUG-user-gen] build() entry', flush=True)
        print(f'[DEBUG-user-gen] steps={len(self.scenario.get("steps", []))}', flush=True)

        print('[DEBUG-user-gen] importing locust...', flush=True)
        # Lazy import: Locust 使用 gevent，与 asyncio 事件循环不兼容，
        # 必须在非 asyncio 上下文中导入，避免导入时死锁
        from locust import HttpUser, between, task
        print('[DEBUG-user-gen] locust imported OK', flush=True)

        steps = self.scenario.get('steps', [])
        self._load_api_requests(steps)

        think_time = self.scenario.get('think_time', {'min': 1, 'max': 3})

        class AdvancedTestUser(HttpUser):
            wait_time = between(
                float(think_time.get('min', 1)),
                float(think_time.get('max', 3)),
            )

            def on_start(self) -> None:
                self.tx_context = TransactionContext()

            def on_stop(self) -> None:
                pass

        # 为每个步骤动态绑定 @task 方法
        for idx, step in enumerate(steps):
            task_method = self._make_task_method(step, idx)
            task_weight = step.get('weight', 1)
            decorated = task(weight=task_weight)(task_method)
            setattr(AdvancedTestUser, f'task_{idx}', decorated)

        return AdvancedTestUser

    def build_all(self) -> List[type]:
        """返回 [HttpUser子类] 列表，兼容 Locust Environment 接口"""
        return [self.build()]

    def _make_task_method(self, step: Dict[str, Any], idx: int) -> Any:
        """生成单个步骤的 task 方法闭包"""
        step_name = step.get('name', f'step_{idx}')
        api_request_id = step.get('api_request_id')
        url_template = step.get('url', '/')
        method_template = step.get('method', 'GET').upper()
        body_template = step.get('body', '')
        headers_template = step.get('headers', {})
        extractors = step.get('extractors', [])

        # 如果引用了 api_request_id，从预加载数据中获取请求定义
        if api_request_id is not None:
            api_req = self._api_requests.get(int(api_request_id))
            if api_req:
                url_template = api_req.url
                method_template = api_req.method.upper() if api_req.method else 'GET'
                body_template = api_req.body or ''

                # 合并 ApiRequest 的 headers
                try:
                    api_headers = json.loads(api_req.headers) if api_req.headers else {}
                    merged = dict(api_headers)
                    merged.update(headers_template)
                    headers_template = merged
                except (json.JSONDecodeError, TypeError):
                    pass

        def task_method(self: Any) -> None:
            # 渲染运行时变量
            url = self.tx_context.render(url_template)
            method = method_template
            headers = self.tx_context.render_dict(headers_template) if headers_template else {}
            body = self.tx_context.render(body_template) if body_template else None

            try:
                response = self.client.request(
                    method,
                    url,
                    data=body,
                    headers=headers,
                    name=step_name,
                )

                # 执行数据提取
                for extractor in extractors:
                    value = extract_value(response, extractor)
                    if value is not None:
                        ext_name = extractor.get('name', '')
                        if ext_name:
                            self.tx_context.set(ext_name, value)

            except Exception:
                pass  # Locust 自动记录失败

        task_method.__name__ = f'task_{idx}'
        task_method.__doc__ = step_name
        return task_method
