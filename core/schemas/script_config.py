"""
Script Config Schema

单一源定义 JSON config 格式，供 AI prompt 和后端校验共用。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

SCRIPT_CONFIG_EXAMPLE: Dict[str, Any] = {
    'name': '用户登录查询流程',
    'description': '登录后查询用户信息',
    'variables': {
        'base_url': 'https://api.example.com',
        'username': 'test_user',
    },
    'setup': [
        {
            'name': '用户登录',
            'request': {
                'method': 'POST',
                'url': '{{base_url}}/api/login',
                'headers': {
                    'Content-Type': 'application/json',
                },
                'json': {
                    'username': '{{username}}',
                    'password': '123456',
                },
            },
            'extract': [
                {
                    'name': 'token',
                    'jsonpath': '$.data.token',
                },
            ],
            'assertions': [
                {
                    'type': 'status_code',
                    'expected': 200,
                },
            ],
        },
    ],
    'steps': [
        {
            'name': '查询用户信息',
            'request': {
                'method': 'GET',
                'url': '{{base_url}}/api/user/info',
                'headers': {
                    'Authorization': 'Bearer {{token}}',
                },
            },
            'assertions': [
                {
                    'type': 'status_code',
                    'expected': 200,
                },
            ],
        },
    ],
    'teardown': [],
}

SCRIPT_CONFIG_SCHEMA_DESCRIPTION: str = f"""
必须是一个合法的 JSON 字符串，表示 API 测试配置，格式如下：

{json.dumps(SCRIPT_CONFIG_EXAMPLE, indent=2, ensure_ascii=False)}

字段说明：
- name: 测试名称（可选）
- description: 测试描述（可选）
- variables: 变量字典（可选），值中可用 {{{{variable}}}} 引用其他变量
- setup: 前置步骤数组（可选），任一失败则中止执行
- steps: 主测试步骤数组（可选）
- teardown: 清理步骤数组（可选），无论结果都会执行

每个步骤（setup/steps/teardown 中的条目）：
{{
    "name": "步骤名称",
    "request": {{
        "method": "GET|POST|PUT|DELETE|PATCH",
        "url": "请求URL，支持 {{{{variable}}}} 模板",
        "headers": {{"key": "value"}},
        "json": {{"key": "value"}}
    }},
    "extract": [{{"name": "变量名", "jsonpath": "JSONPath 表达式，如 $.data.token"}}],
    "assertions": [{{"type": "status_code|jsonpath", "expected": 200}}]
}}

注意：只输出 JSON 本身，不要用 markdown 包裹。
"""


def validate_script_config(code: str) -> Tuple[bool, str]:
    try:
        config = json.loads(code)
    except json.JSONDecodeError as e:
        return False, f'JSON format error: {e}'

    if not isinstance(config, dict):
        return False, f'Must be a JSON object, got {type(config).__name__}'

    for section in ('setup', 'steps', 'teardown'):
        items = config.get(section, [])
        if not isinstance(items, list):
            return False, f"'{section}' must be a list"
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                return False, f"'{section}[{i}]' must be an object"
            if 'name' not in item:
                return False, f"'{section}[{i}]' missing 'name'"
            request = item.get('request')
            if request is not None:
                if not isinstance(request, dict):
                    return False, f"'{section}[{i}].request' must be an object"
                if 'method' not in request:
                    return False, f"'{section}[{i}].request' missing 'method'"
                if 'url' not in request:
                    return False, f"'{section}[{i}].request' missing 'url'"

    return True, ''
