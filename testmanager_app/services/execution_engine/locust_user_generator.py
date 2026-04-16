"""
Locust用户生成器
根据配置动态生成Locust User类代码
使用 CSV 输出方案 - 不依赖 HTTP 回调机制
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class LocustUserGenerator:
    """生成Locust测试代码"""
    
    def __init__(self, config: Any):
        self.config = config
        self.scenario = config.scenario or {}
    
    def generate(self) -> str:
        """生成完整的Locust文件内容"""
        code_lines = []
        
        # 导入语句
        code_lines.extend(self._generate_imports())
        code_lines.append("")
        
        # 事务上下文类
        code_lines.extend(self._generate_context_class())
        code_lines.append("")
        
        # 数据提取器函数
        code_lines.extend(self._generate_extractors())
        code_lines.append("")
        
        # User类
        code_lines.extend(self._generate_user_class())
        
        return "\n".join(code_lines)
    
    def _generate_imports(self) -> List[str]:
        """生成导入语句 - 移除 requests 和 events（不再需要回调）"""
        return [
            "from locust import HttpUser, task, between",
            "import json",
            "import re",
            "from typing import Dict, Any, Optional",
        ]
    
    def _generate_context_class(self) -> List[str]:
        """生成事务上下文类"""
        return [
            "class TransactionContext:",
            "    \"\"\"事务上下文，用于步骤间数据传递\"\"\"",
            "    ",
            "    def __init__(self):",
            "        self.variables: Dict[str, Any] = {}",
            "    ",
            "    def set(self, name: str, value: Any) -> None:",
            "        self.variables[name] = value",
            "    ",
            "    def get(self, name: str, default: Any = None) -> Any:",
            "        return self.variables.get(name, default)",
            "    ",
            "    def render(self, template: str) -> str:",
            "        if not template:",
            "            return template",
            "        result = template",
            "        for name, value in self.variables.items():",
            "            placeholder = f'${{{name}}}'",
            "            if placeholder in result:",
            "                result = result.replace(placeholder, str(value))",
            "        return result",
            "    ",
            "    def render_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:",
            "        if not data:",
            "            return data",
            "        result = {}",
            "        for key, value in data.items():",
            "            if isinstance(value, str):",
            "                result[key] = self.render(value)",
            "            elif isinstance(value, dict):",
            "                result[key] = self.render_dict(value)",
            "            elif isinstance(value, list):",
            "                result[key] = [",
            "                    self.render(item) if isinstance(item, str) else item",
            "                    for item in value",
            "                ]",
            "            else:",
            "                result[key] = value",
            "        return result",
        ]
    
    def _generate_extractors(self) -> List[str]:
        """生成数据提取器函数"""
        return [
            "def extract_value(response, extractor: Dict[str, Any]) -> Any:",
            "    \"\"\"从响应中提取数据\"\"\"",
            "    ext_type = extractor.get('type')",
            "    expression = extractor.get('expression', '')",
            "    ",
            "    if ext_type == 'json_path':",
            "        try:",
            "            import jsonpath_ng",
            "            json_data = response.json()",
            "            jsonpath_expr = jsonpath_ng.parse(expression)",
            "            matches = [match.value for match in jsonpath_expr.find(json_data)]",
            "            return matches[0] if matches else None",
            "        except Exception as e:",
            "            print(f'JSONPath extraction failed: {e}')",
            "            return None",
            "    elif ext_type == 'regex':",
            "        try:",
            "            match = re.search(expression, response.text)",
            "            return match.group(1) if match and match.groups() else match.group(0) if match else None",
            "        except Exception as e:",
            "            print(f'Regex extraction failed: {e}')",
            "            return None",
            "    elif ext_type == 'header':",
            "        return response.headers.get(expression)",
            "    elif ext_type == 'status_code':",
            "        return response.status_code",
            "    elif ext_type == 'response_time':",
            "        return response.elapsed.total_seconds() * 1000",
            "    elif ext_type == 'xpath':",
            "        try:",
            "            from lxml import html",
            "            tree = html.fromstring(response.content)",
            "            result = tree.xpath(expression)",
            "            return result[0] if result else None",
            "        except Exception as e:",
            "            print(f'XPath extraction failed: {e}')",
            "            return None",
            "    return None",
        ]
    
    def _generate_user_class(self) -> List[str]:
        """生成User类"""
        code_lines = []
        
        # 类定义
        code_lines.append("class AdvancedTestUser(HttpUser):")
        code_lines.append('    """高级压测用户"""')
        code_lines.append("")
        
        # 等待时间
        think_time = self.scenario.get('think_time', {'min': 1, 'max': 3})
        code_lines.append(f"    wait_time = between({think_time.get('min', 1)}, {think_time.get('max', 3)})")
        code_lines.append("")
        
        # on_start方法
        code_lines.append("    def on_start(self):")
        code_lines.append('        """初始化事务上下文"""')
        code_lines.append("        self.tx_context = TransactionContext()")
        code_lines.append("")
        
        # 生成任务方法
        steps = self.scenario.get('steps', [])
        for idx, step in enumerate(steps):
            task_code = self._generate_task_method(step, idx)
            code_lines.extend(task_code)
            code_lines.append("")
        
        return code_lines
    
    def _generate_task_method(self, step: Dict[str, Any], idx: int) -> List[str]:
        """生成单个任务方法"""
        code_lines = []
        
        step_name = step.get('name', f'step_{idx}')
        weight = step.get('weight', 1)
        step_url = step.get('url', '/')
        step_method = step.get('method', 'GET').upper()
        headers = step.get('headers', {})
        extractors = step.get('extractors', [])
        body = step.get('body', '')
        
        code_lines.append(f"    @task({weight})")
        code_lines.append(f"    def {self._sanitize_name(step_name)}(self):")
        code_lines.append(f'        """{step_name}"""')
        code_lines.append('')
        
        code_lines.append(f'        url = "{step_url}"')
        code_lines.append('')
        
        if headers:
            headers_json = json.dumps(headers)
            code_lines.append(f'        headers = {headers_json}')
        
        code_lines.append('        try:')
        
        if step_method == 'GET':
            if headers:
                code_lines.append(f'            response = self.client.get(url, headers=headers, name="{step_name}")')
            else:
                code_lines.append(f'            response = self.client.get(url, name="{step_name}")')
        elif step_method == 'POST':
            code_lines.append(f'            body = "{body}"')
            if headers:
                code_lines.append(f'            response = self.client.post(url, data=body, headers=headers, name="{step_name}")')
            else:
                code_lines.append(f'            response = self.client.post(url, data=body, name="{step_name}")')
        elif step_method == 'PUT':
            code_lines.append(f'            body = "{body}"')
            if headers:
                code_lines.append(f'            response = self.client.put(url, data=body, headers=headers, name="{step_name}")')
            else:
                code_lines.append(f'            response = self.client.put(url, data=body, name="{step_name}")')
        elif step_method == 'DELETE':
            if headers:
                code_lines.append(f'            response = self.client.delete(url, headers=headers, name="{step_name}")')
            else:
                code_lines.append(f'            response = self.client.delete(url, name="{step_name}")')
        else:
            if headers:
                code_lines.append(f'            response = self.client.request("{step_method}", url, headers=headers, name="{step_name}")')
            else:
                code_lines.append(f'            response = self.client.request("{step_method}", url, name="{step_name}")')
        
        if extractors:
            code_lines.append('')
            code_lines.append('            # 数据提取')
            for extractor in extractors:
                ext_type = extractor.get('type', '')
                ext_name = extractor.get('name', '')
                ext_expr = extractor.get('expression', '')
                
                if ext_type == 'json_path':
                    code_lines.append(f'            try:')
                    code_lines.append(f'                import jsonpath_ng')
                    code_lines.append(f'                json_data = response.json()')
                    code_lines.append(f'                jsonpath_expr = jsonpath_ng.parse("{ext_expr}")')
                    code_lines.append(f'                matches = [match.value for match in jsonpath_expr.find(json_data)]')
                    code_lines.append(f'                if matches:')
                    code_lines.append(f'                    self.tx_context.set("{ext_name}", matches[0])')
                    code_lines.append(f'            except Exception:')
                    code_lines.append(f'                pass')
                elif ext_type == 'regex':
                    code_lines.append(f'            try:')
                    code_lines.append(f'                match = re.search("{ext_expr}", response.text)')
                    code_lines.append(f'                if match:')
                    code_lines.append(f'                    self.tx_context.set("{ext_name}", match.group(1) if match.groups() else match.group(0))')
                    code_lines.append(f'            except Exception:')
                    code_lines.append(f'                pass')
                elif ext_type == 'header':
                    code_lines.append(f'            self.tx_context.set("{ext_name}", response.headers.get("{ext_expr}"))')
                elif ext_type == 'status_code':
                    code_lines.append(f'            self.tx_context.set("{ext_name}", response.status_code)')
        
        code_lines.append('')
        code_lines.append('        except Exception as e:')
        code_lines.append('            print(f"Request error: {str(e)}")')
        code_lines.append('')
        return code_lines
    
    def _sanitize_name(self, name: str) -> str:
        """将名称转换为有效的Python标识符"""
        import re
        if not name:
            return 'task'
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()


class DynamicLocustUserGenerator:
    """动态Locust User生成器（运行时版本）"""
    
    def __init__(self, config: Any):
        self.config = config
        self.scenario = config.scenario or {}
    
    def generate_user_class(self) -> type:
        """动态生成并返回User类（非代码字符串）"""
        from locust import HttpUser, task, between
        import json
        import re
        from typing import Dict, Any
        
        # 获取API请求数据
        from testmanager_app.models import ApiRequest
        
        steps = self.scenario.get('steps', [])
        think_time = self.scenario.get('think_time', {'min': 1, 'max': 3})
        
        # 预加载所有API请求
        api_requests = {}
        for step in steps:
            api_id = step.get('api_request_id')
            if api_id:
                try:
                    api_request = ApiRequest.objects.get(id=api_id)
                    api_requests[api_id] = api_request
                except ApiRequest.DoesNotExist:
                    pass
        
        # 定义事务上下文
        class TransactionContext:
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
                result = {}
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
        
        # 定义数据提取函数
        def extract_value(response: Any, extractor: Dict[str, Any]) -> Any:
            ext_type = extractor.get('type')
            expression = extractor.get('expression', '')
            
            if ext_type == 'json_path':
                try:
                    from jsonpath_ng import parse as jsonpath_parse
                    json_data = response.json()
                    jsonpath_expr = jsonpath_parse(expression)
                    matches = [match.value for match in jsonpath_expr.find(json_data)]
                    return matches[0] if matches else None
                except Exception as e:
                    print(f'JSONPath extraction failed: {e}')
                    return None
            elif ext_type == 'regex':
                try:
                    match = re.search(expression, response.text)
                    return match.group(1) if match and match.groups() else match.group(0) if match else None
                except Exception as e:
                    print(f'Regex extraction failed: {e}')
                    return None
            elif ext_type == 'header':
                return response.headers.get(expression)
            elif ext_type == 'status_code':
                return response.status_code
            elif ext_type == 'response_time':
                return response.elapsed.total_seconds() * 1000
            elif ext_type == 'xpath':
                try:
                    from lxml import html
                    tree = html.fromstring(response.content)
                    result = tree.xpath(expression)
                    return result[0] if result else None
                except Exception as e:
                    print(f'XPath extraction failed: {e}')
                    return None
            return None
        
        # 创建User类
        class AdvancedTestUser(HttpUser):
            wait_time = between(think_time.get('min', 1), think_time.get('max', 3))
            
            def on_start(self) -> None:
                self.tx_context = TransactionContext()
            
            def on_stop(self) -> None:
                pass
        
        # 动态添加任务方法
        for idx, step in enumerate(steps):
            task_method = self._create_task_method(step, idx, api_requests, extract_value)
            setattr(AdvancedTestUser, f'task_{idx}', task(task_method, weight=step.get('weight', 1)))
        
        return AdvancedTestUser
    
    def _create_task_method(self, step: Dict[str, Any], idx: int, api_requests: Dict[int, Any], extract_value_func: Any) -> Any:
        """创建任务方法"""
        step_name = step.get('name', f'step_{idx}')
        api_request_id = step.get('api_request_id')
        headers_template = step.get('headers', {})
        extractors = step.get('extractors', [])
        
        def task_method(self: Any) -> None:
            # 获取API请求信息
            if api_request_id is None:
                return
            api_request = api_requests.get(api_request_id)
            if not api_request:
                return
            
            # 渲染headers
            headers = self.tx_context.render_dict(headers_template) if headers_template else {}
            
            # 解析API请求的headers
            try:
                api_headers = json.loads(api_request.headers) if api_request.headers else {}
                headers.update(api_headers)
            except:
                pass
            
            # 发送请求
            method = api_request.method.upper()
            url = api_request.url
            body = api_request.body
            
            try:
                if method == 'GET':
                    response = self.client.get(url, headers=headers, name=step_name)
                elif method == 'POST':
                    response = self.client.post(url, data=body, headers=headers, name=step_name)
                elif method == 'PUT':
                    response = self.client.put(url, data=body, headers=headers, name=step_name)
                elif method == 'PATCH':
                    response = self.client.patch(url, data=body, headers=headers, name=step_name)
                elif method == 'DELETE':
                    response = self.client.delete(url, headers=headers, name=step_name)
                else:
                    response = self.client.request(method, url, data=body, headers=headers, name=step_name)
                
                # 执行数据提取
                for extractor in extractors:
                    value = extract_value_func(response, extractor)
                    if value is not None:
                        self.tx_context.set(extractor.get('name'), value)
                        
            except Exception as e:
                print(f'Request failed: {e}')
        
        task_method.__name__ = f'task_{idx}'
        task_method.__doc__ = step_name
        return task_method