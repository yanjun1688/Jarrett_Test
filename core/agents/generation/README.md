# Generation 模块 - 测试代码生成

## 概述

`generation` 模块负责测试代码的自动生成，提供从测试用例到可执行代码的完整转换流程。支持多种测试框架和编程语言。

## 模块结构

```
generation/
├── __init__.py                    # 模块入口
├── test_code_generation_agent.py  # 测试代码生成 Agent
├── prompt_builder.py              # 提示构建器
└── code_quality_validator.py      # 代码质量验证器
```

## 核心组件

### TestCodeGenerationAgent

主要的测试代码生成 Agent，负责：

- 解析测试用例结构
- 分析项目代码风格
- 生成符合规范的测试代码
- 验证代码质量并迭代优化

```python
from core.agents.generation import TestCodeGenerationAgent

agent = TestCodeGenerationAgent(
    llm_service=llm_service,
    rag_retriever=rag_retriever
)

result = await agent.generate_test_code(
    test_case={
        "name": "登录测试",
        "description": "测试用户登录功能",
        "steps": ["打开登录页面", "输入用户名密码", "点击登录按钮"],
        "expected_result": "登录成功，跳转到首页"
    },
    framework="pytest",
    language="python",
    project_path="/path/to/project"
)
```

#### 支持的测试框架

| 框架 | 语言 | 特性 |
|------|------|------|
| pytest | Python | Fixture 支持、参数化测试 |
| unittest | Python | TestCase 类结构、setUp/tearDown |
| Jest | JavaScript | 快照测试、Mock 支持 |
| Mocha | JavaScript | 异步测试、Chai 断言 |

### PromptBuilder

构建代码生成的提示模板：

- 格式化测试用例信息
- 注入代码风格指南
- 添加框架特定指令
- 提供输出格式要求

```python
from core.agents.generation import PromptBuilder

prompt = PromptBuilder.build_generation_prompt(
    test_case=test_case,
    framework="pytest",
    framework_config={
        "import_style": "import pytest",
        "test_function_pattern": "def test_",
        "assertion_style": "assert"
    },
    style_info={"indent": 4, "max_line_length": 100},
    pattern_info={"common_patterns": [...]}
)

system_message = PromptBuilder.get_system_message("pytest")
```

### CodeQualityValidator

验证生成代码的质量：

- 语法检查
- 导入验证
- 测试函数命名检查
- 断言语句验证
- 代码风格检查
- 行长度检查

```python
from core.agents.generation import CodeQualityValidator

validator = CodeQualityValidator()
result = validator.validate_code_quality(
    code=generated_code,
    language="python",
    framework="pytest"
)

# result 包含:
# - score: 质量分数 (0-100)
# - issues: 问题列表
# - summary: 统计摘要
# - passed: 是否通过验证
```

## 生成流程

```
测试用例
    │
    ▼
┌─────────────────┐
│  输入验证        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  项目分析        │ ← 分析代码风格和模式
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  构建提示        │ ← PromptBuilder
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM 生成        │ ← 调用语言模型
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  代码提取        │ ← 从响应中提取代码
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  质量验证        │ ← CodeQualityValidator
└────────┬────────┘
         │
    ┌────┴────┐
    │ 是否通过？│
    └────┬────┘
         │
    ┌────┴────┐
    No        Yes
    │         │
    ▼         ▼
 重试生成   返回结果
```

## 质量规则

### Python 规则

```python
{
    "imports": {
        "required": ["import", "from"],
        "forbidden": ["import *"]
    },
    "test_functions": {
        "pattern": r'def\s+test_',
        "required": True
    },
    "assertions": {
        "pattern": r'assert\s+',
        "required": True
    },
    "docstrings": {
        "pattern": r'""".*?"""',
        "required": True
    }
}
```

### JavaScript 规则

```python
{
    "test_functions": {
        "pattern": r'it\(|test\(|describe\(',
        "required": True
    },
    "assertions": {
        "pattern": r'expect\(|assert\.',
        "required": True
    }
}
```

## 使用示例

### 批量生成测试

```python
agent = TestCodeGenerationAgent(llm_service=llm_service)

results = await agent.generate_multiple_tests(
    test_cases=[test_case_1, test_case_2, test_case_3],
    framework="pytest",
    language="python",
    parallel=True  # 并行生成
)
```

### 带质量反馈的生成

```python
# 生成会自动进行质量检查和重试
result = await agent.generate_test_code(
    test_case=test_case,
    framework="pytest",
    validate_quality=True,
    max_retries=3
)

print(f"质量分数: {result['quality_score']}")
print(f"重试次数: {result['metadata']['attempts']}")
```

### 自定义框架配置

```python
framework_config = {
    "import_style": "import pytest",
    "test_function_pattern": "def test_",
    "assertion_style": "assert",
    "fixture_support": True
}

prompt = PromptBuilder.build_generation_prompt(
    test_case=test_case,
    framework="pytest",
    framework_config=framework_config
)
```

## 输出格式

```python
{
    "code": "def test_login():\n    ...",
    "test_case": {...},
    "framework": "pytest",
    "language": "python",
    "quality_score": 85,
    "quality_issues": [
        {
            "severity": "warning",
            "message": "Line 10 exceeds 100 characters",
            "line": 10,
            "suggestion": "Break long lines"
        }
    ],
    "metadata": {
        "generation_time": 2.5,
        "attempts": 1
    }
}
```

## 扩展指南

### 添加新框架支持

1. 在 `PromptBuilder.get_system_message()` 添加框架消息
2. 在 `CodeQualityValidator._initialize_quality_rules()` 添加质量规则
3. 在 `TestCodeGenerationAgent._get_framework_config()` 添加框架配置

### 自定义质量验证

```python
class CustomValidator(CodeQualityValidator):
    def _validate_custom_rules(self, code: str) -> List[QualityIssue]:
        issues = []
        # 自定义验证逻辑
        return issues
```