"""
场景配置中心
集中管理所有生成场景的 prompt 模板、schema、校验逻辑和保存配置。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

API_SCRIPT_EXAMPLE: Dict[str, Any] = {
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
                'headers': {'Content-Type': 'application/json'},
                'json': {'username': '{{username}}', 'password': '123456'},
            },
            'extract': [{'name': 'token', 'jsonpath': '$.data.token'}],
            'assertions': [{'type': 'status_code', 'expected': 200}],
        },
    ],
    'steps': [
        {
            'name': '查询用户信息',
            'request': {
                'method': 'GET',
                'url': '{{base_url}}/api/user/info',
                'headers': {'Authorization': 'Bearer {{token}}'},
            },
            'assertions': [{'type': 'status_code', 'expected': 200}],
        },
    ],
    'teardown': [],
}

FIELD_MAPPING_KEY_SELF = "__self__"
FIELD_MAPPING_KEY_NONE = "__none__"


def _validate_script_config(data: Dict[str, Any]) -> Tuple[bool, str]:
    """校验 API 测试脚本配置（接收已 parse 的 dict）"""
    for section in ('setup', 'steps', 'teardown'):
        items = data.get(section, [])
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


def _validate_test_cases_output(data: Dict[str, Any]) -> Tuple[bool, str]:
    """校验 PRD 测试用例输出（接收已 parse 的 dict）"""
    cases = data.get('test_cases')
    if not isinstance(cases, list):
        return False, "Missing 'test_cases' array"

    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            return False, f"test_cases[{i}] must be an object"
        if 'title' not in case:
            return False, f"test_cases[{i}] missing 'title'"
        if 'steps' not in case:
            return False, f"test_cases[{i}] missing 'steps'"
        if 'expected_result' not in case:
            return False, f"test_cases[{i}] missing 'expected_result'"

    return True, ''


SCENARIOS: Dict[str, Dict[str, Any]] = {
    "prd_test_cases": {
        "name": "PRD 测试用例",
        "description": "根据 PRD 文档生成功能测试用例",
        "prompt_template": """请根据以下 PRD 内容生成测试用例，以 JSON 格式输出。

PRD 内容：
{content}

请生成 JSON 格式的测试用例列表，格式如下：
{schema_example}

要求：
1. 覆盖所有主要功能点
2. 包含正常场景、异常场景和边界值测试
3. 每个用例必须包含 title、steps、expected_result 字段
4. title 以 TC-001、TC-002 等编号开头
5. steps 要清晰可执行（多步用换行分隔）
6. 输出合法 JSON，不要用 markdown 包裹
7. 不要输出任何说明文字，只输出 JSON""",
        "schema": {
            "type": "object",
            "properties": {
                "test_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "pre_steps": {"type": "string"},
                            "steps": {"type": "string"},
                            "expected_result": {"type": "string"},
                        },
                        "required": ["title", "steps", "expected_result"],
                    },
                }
            },
            "required": ["test_cases"],
        },
        "schema_example": json.dumps(
            {
                "test_cases": [
                    {
                        "title": "TC-001: 用户登录成功",
                        "pre_steps": "打开登录页面，确保网络正常",
                        "steps": "1. 输入已注册用户名\n2. 输入正确密码\n3. 点击登录按钮",
                        "expected_result": "登录成功，跳转到首页",
                    },
                    {
                        "title": "TC-002: 用户登录-密码错误",
                        "pre_steps": "打开登录页面",
                        "steps": "1. 输入已注册用户名\n2. 输入错误密码\n3. 点击登录按钮",
                        "expected_result": "登录失败，提示'用户名或密码错误'",
                    },
                ]
            },
            indent=2,
            ensure_ascii=False,
        ),
        "system_message": "你是专业的软件测试工程师，擅长分析需求文档并生成全面的测试用例。",
        "validate": _validate_test_cases_output,
        "save_config": {
            "serializer": "FeatureTestCaseSerializer",
            "serializer_module": "testmanager_app.serializers",
            "root_key": "test_cases",
            "field_mapping": {
                "title": "title",
                "steps": "steps",
                "expected_result": "expected_result",
                "pre_steps": "pre_steps",
            },
            "project_field": "project",
            "created_by_field": "created_by_id",
            "auto_fields": {},
            "save_kwargs": {"source": "{source}"},
        },
    },
    "api_test_scripts": {
        "name": "API 测试脚本",
        "description": "根据 API 定义生成测试脚本配置",
        "prompt_template": """请根据以下 API 信息生成 API 测试配置（JSON 格式）。

{content}

请参考以下格式生成 JSON 对象：
{schema_example}

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
    "extract": [{{"name": "变量名", "jsonpath": "JSONPath 表达式"}}],
    "assertions": [{{"type": "status_code|jsonpath", "expected": 200}}]
}}

要求：
1. 断言规则：优先使用 jsonpath 验证业务状态码（$.code），除非需要验证 HTTP 响应码（如 401）才用 status_code
2. 使用 {{{{variable}}}} 模板语法引用变量
3. 输出格式化的 JSON（带缩进），不要用 markdown 包裹
4. 不要输出任何说明文字，只输出 JSON""",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "variables": {"type": "object"},
                "setup": {"type": "array"},
                "steps": {"type": "array"},
                "teardown": {"type": "array"},
            },
        },
        "schema_example": json.dumps(API_SCRIPT_EXAMPLE, indent=2, ensure_ascii=False),
        "system_message": "你是 API 测试专家，擅长生成 JSON 格式的 API 测试配置。",
        "validate": _validate_script_config,
        "save_config": {
            "serializer": "TestScriptCreateSerializer",
            "serializer_module": "testmanager_app.serializers",
            "root_key": None,
            "field_mapping": {
                "content": "__self__",
            },
            "project_field": "project",
            "created_by_field": "created_by_id",
            "auto_fields": {
                "name": "Generated Script {timestamp}",
                "description": "Generated from ChatBot at {timestamp}",
                "script_type": "api",
            },
            "save_kwargs": {
                "source": "{source}",
                "is_active": True,
            },
        },
    },
}


def list_scenarios() -> str:
    lines = ["## 可用生成场景\n"]
    for key, config in SCENARIOS.items():
        lines.append(f"- **{config['name']}** (scenario=\"{key}\"): {config['description']}")
    lines.append("")
    lines.append("调用方式：")
    lines.append("1. generate(scenario=<场景名>, content=<输入内容>) → 返回 JSON")
    lines.append("2. save(scenario=<场景名>, output=<JSON>, project_id=<项目ID>) → 保存到数据库")
    return "\n".join(lines)


def validate_output(scenario: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    config = SCENARIOS.get(scenario)
    if not config:
        return False, f"Unknown scenario: {scenario}"
    validate_fn = config.get("validate")
    if validate_fn:
        result: Tuple[bool, str] = validate_fn(data)
        return result
    return True, ""
