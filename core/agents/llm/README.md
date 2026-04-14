# LLM 模块 - 大语言模型服务层

## 概述

`llm` 模块提供统一的大语言模型服务抽象，支持多个主流 LLM 提供商。采用工厂模式和策略模式，便于扩展和切换不同的 LLM 服务。

## 模块结构

```
llm/
├── __init__.py              # 模块入口
├── base_llm.py              # 基础 LLM 服务类
├── openai_llm.py            # OpenAI 实现
├── anthropic_llm.py         # Anthropic Claude 实现
├── deepseek_llm.py          # DeepSeek 实现
├── zhipu_llm.py             # 智谱 AI 实现
├── qwen_llm.py              # 阿里云 Qwen 实现
└── context_aware_llm.py     # 上下文感知 LLM 服务
```

## 支持的提供商

| 提供商 | 模型示例 | API 格式 |
|--------|----------|----------|
| OpenAI | GPT-4, GPT-3.5 | OpenAI API |
| Anthropic | Claude 3.5 Sonnet | Anthropic API |
| DeepSeek | DeepSeek Chat | OpenAI 兼容 |
| 智谱 AI | GLM-4 | OpenAI 兼容 |
| 阿里云 | Qwen-Coder | OpenAI 兼容 |

## 核心类

### BaseLLMService

所有 LLM 服务的抽象基类：

```python
from core.agents.llm import BaseLLMService, LLMConfig, LLMProvider

config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key="your-api-key",
    temperature=0.3,
    max_tokens=4096
)

llm = OpenAILLMService(config=config)
```

### OpenAICompatibleService

OpenAI 兼容 API 的基类，适用于 DeepSeek、Qwen、智谱等：

```python
class DeepSeekLLMService(OpenAICompatibleService):
    def __init__(self, config=None, provider=None):
        self.base_url = "https://api.deepseek.com"
        super().__init__(config, provider)
```

## 使用方法

### 创建 LLM 服务

```python
from core.agents.llm import create_llm_service

# 使用默认配置
llm = create_llm_service("openai")

# 指定模型
llm = create_llm_service(
    provider="deepseek",
    model_name="deepseek-chat",
    api_key="your-key"
)
```

### 生成文本

```python
# 基本生成
response = await llm.generate(
    prompt="解释什么是测试驱动开发",
    system_message="你是一个测试专家"
)

# 带对话历史
response = await llm.generate(
    prompt="继续解释",
    system_message="你是一个测试专家",
    conversation_history=[
        {"role": "user", "content": "解释什么是TDD"},
        {"role": "assistant", "content": "TDD是..."}
    ]
)
```

### 使用工具（Function Calling）

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "generate_test",
            "description": "生成测试用例",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string"},
                    "test_type": {"type": "string"}
                }
            }
        }
    }
]

result = await llm.generate_with_tools(
    prompt="生成登录功能的测试用例",
    tools=tools,
    system_message="你是一个测试助手"
)

# result 包含:
# - response: 文本回复
# - tool_calls: 工具调用列表
# - finish_reason: 完成原因
```

### 上下文感知生成

```python
from core.agents.llm import ContextAwareLLMService

llm = ContextAwareLLMService(
    rag_retriever=rag_retriever,
    max_context_length=8000,
    context_compression=True
)

# 自动检索相关文档并增强提示
response = await llm.generate_with_rag(
    query="如何编写好的单元测试？",
    top_k=5,
    use_rag=True
)
```

## 配置

### 环境变量

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL_NAME=gpt-4

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL_NAME=claude-3-5-sonnet-20241022

# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL_NAME=deepseek-chat

# 智谱 AI
ZHIPU_API_KEY=...
ZHIPU_MODEL_NAME=glm-4.7-flash

# 阿里云 Qwen
DASHSCOPE_API_KEY=sk-...
QWEN_MODEL_NAME=qwen3-coder-plus

# 通用配置
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096
```

### 代码配置

```python
from core.agents.llm import LLMConfig, LLMProvider

config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4-turbo",
    api_key="your-key",
    temperature=0.3,
    max_tokens=4096,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    extra_params={
        "response_format": {"type": "json_object"}
    }
)
```

## 特性

### Token 计算

```python
token_count = llm.count_tokens("这是一段需要计算 token 的文本")
```

### 成本估算

```python
cost = llm.estimate_cost(
    input_tokens=1000,
    output_tokens=500
)
# 返回美元成本
```

### 智谱 AI 深度思考模式

```python
from core.agents.llm import ZhipuLLMService

llm = ZhipuLLMService()
response = await llm.generate(
    prompt="复杂推理问题",
    thinking_enabled=True  # 启用深度思考
)
```

## 各提供商特性

### OpenAI

- 标准 OpenAI API
- 支持 GPT-4、GPT-3.5-turbo 等
- 支持 Function Calling

### Anthropic Claude

- 使用 Anthropic 异步客户端
- 支持 Claude 3.5 系列
- 独立的 system 参数

### DeepSeek

- OpenAI 兼容 API
- 端点: `https://api.deepseek.com`
- 高性价比

### 智谱 AI

- OpenAI 兼容 API
- 端点: `https://open.bigmodel.cn/api/paas/v4/`
- 支持深度思考模式

### 阿里云 Qwen

- OpenAI 兼容 API
- 端点: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 适合代码生成

## 错误处理

```python
from shared.exceptions import JTestError

try:
    response = await llm.generate(prompt="...")
except Exception as e:
    logger.error(f"LLM 调用失败: {e}")
    # 处理错误
```

## 扩展指南

### 添加新提供商

1. 创建新的服务类：

```python
from core.agents.llm.base_llm import OpenAICompatibleService

class NewProviderLLMService(OpenAICompatibleService):
    def __init__(self, config=None, provider=None):
        self.base_url = "https://api.newprovider.com"
        super().__init__(config, provider)
```

2. 在 `base_llm.py` 的 `create_llm_service()` 中注册：

```python
elif provider_enum == LLMProvider.NEW_PROVIDER:
    from .new_provider_llm import NewProviderLLMService
    service_class = NewProviderLLMService
```

## 最佳实践

1. **温度设置**: 代码生成用低温度 (0.2)，创意生成用高温度 (0.7)
2. **Token 限制**: 注意模型的上下文窗口限制
3. **错误重试**: 实现适当的重试机制
4. **成本控制**: 监控 Token 使用量