# 意图分类系统 (Intent Classification System)

基于**集合论 + 谓词逻辑**的形式化规范实现的意图分类模块。

## 概述

本系统采用三维模型 `(V, O, M)` 从用户消息中提取语义单元，通过推导规则确定意图类型。

### 核心概念

| 维度 | 含义 | 示例 |
|------|------|------|
| V (Verb) | 动作集合 | 生成、查找、执行、帮助 |
| O (Object) | 对象集合 | 测试用例、接口测试、PRD |
| M (Modality) | 语气集合 | 疑问、祈使、中性 |

### 设计原则

1. **集合互不相交**：动作集合 V 的子集 `V_gen`、`V_qry`、`V_exe`、`V_help` 严格互斥
2. **特异度优先**：特定类型（UI、API）优先于通用类型（测试用例）
3. **规则优先，LLM 兜底**：先尝试规则推导，失败时调用 LLM

## 快速开始

```python
from core.agents.intent import IntentClassifier

# 创建分类器
classifier = IntentClassifier()

# 简单分类
intent = classifier.classify("生成测试用例")
# → "generate_testcase"

# 详细分类
result = classifier.classify_with_details("如何生成PRD")
print(result.intent)    # "query_knowledge"
print(result.rule_id)   # "Q4"
print(result.score)     # 0.6

# 带 LLM fallback 的异步分类
result = await classifier.classify_with_llm("帮我分析这段代码", llm_service)
```

## 架构设计

```
core/agents/intent/
├── __init__.py      # 模块导出
├── types.py         # 数据类型定义（Triple, ClassificationResult）
├── sets.py          # 集合定义（V, O, M）
├── extractor.py     # 三元组提取器
├── rules.py         # 推导规则
└── classifier.py    # 分类器主类
```

### 处理流程

```
用户消息
    ↓
┌─────────────────────────────┐
│  预处理（移除代码块）        │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│  提取三元组 (V, O, M)        │
│  - verbs: {V_GEN}           │
│  - objects: [O_TC]          │
│  - modality: M_NEUTRAL      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│  推导规则                    │
│  G3: Generate + TC          │
│  → GENERATE_TESTCASE        │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│  置信度判断                  │
│  score >= threshold?        │
└─────────────────────────────┘
    ↓         ↓
  返回结果   LLM fallback
```

## 集合定义

### 动作集合 V

| 子集 | 含义 | 关键词 |
|------|------|--------|
| `V_GEN` | 生成/创作 | 生成、创建、编写、设计 |
| `V_QRY` | 查询/检索 | 查找、查询、看看、搜索 |
| `V_EXE` | 执行/运行 | 执行、运行、开始、启动 |
| `V_HELP` | 帮助/说明 | 帮助、怎么用、使用说明 |

### 对象集合 O

| 子集 | 含义 | 特异度 |
|------|------|--------|
| `O_UI` | UI/Web 测试 | 高 |
| `O_API` | API/接口测试 | 高 |
| `O_TC` | 通用测试用例 | 中 |
| `O_PRD` | PRD 文档 | 低 |
| `O_KNOW` | 知识库 | 低 |

### 语气集合 M

| 子集 | 含义 | 示例 |
|------|------|------|
| `M_INTERROGATIVE` | 疑问模式 | 如何、怎么、什么是 |
| `M_IMPERATIVE` | 祈使模式 | 帮我、给我、请 |
| `M_NEUTRAL` | 中性模式 | （无特征词） |
| `M_HELP` | 帮助模式 | 怎么用 |

## 推导规则

### 生成类意图（G1-G4）

```
G1: Generate(v) ∧ IsUITest(o) → GENERATE_UI_TEST
G2: Generate(v) ∧ IsAPITest(o) → GENERATE_API_TEST
G3: Generate(v) ∧ IsGenericTest(o) → GENERATE_TESTCASE
G4: Generate(v) ∧ IsPRD(o) → GENERATE_PRD
```

### 查询类意图（Q1-Q4）

```
Q1: Query(v) ∧ IsAnyTest(o) → QUERY_TESTCASE
Q2: Query(v) ∧ IsPRD(o) → QUERY_PRD
Q3: Query(v) ∧ IsKnowledge(o) → QUERY_KNOWLEDGE
Q4: Interrogative(m) → QUERY_KNOWLEDGE  // 疑问模式兜底
```

### 执行类意图（E1）

```
E1: Execute(v) → EXECUTE_TEST  // 对象可选
```

### 帮助类意图（H1）

```
H1: Help(v) → HELP
```

### 兜底（F1）

```
F1: 无匹配 → CHAT
```

## LLM Fallback 触发条件

| 条件 | 说明 |
|------|------|
| `intent == CHAT && len(message) > threshold` | 复杂表达但规则返回 CHAT |
| `score < confidence_threshold` | 置信度不足 |

## 配置

在 `settings.py` 中配置：

```python
INTENT_CONFIG = {
    "LLM_FALLBACK_MESSAGE_LEN": 10,      # LLM fallback 消息长度阈值
    "CONFIDENCE_THRESHOLD": 0.6,         # 置信度阈值
    "CACHE_ENABLED": True,               # 启用缓存
    "CACHE_TTL": 300,                    # 缓存 TTL（秒）
}
```

环境变量覆盖：

```bash
INTENT_LLM_FALLBACK_LEN=15
INTENT_CONFIDENCE_THRESHOLD=0.7
INTENT_CACHE_ENABLED=true
INTENT_CACHE_TTL=600
```

## 典型用例

| 输入 | 三元组 | 规则 | 意图 |
|------|--------|------|------|
| 生成功能测试用例 | V_GEN, O_TC, M_NEUTRAL | G3 | `GENERATE_TESTCASE` |
| 生成接口测试 | V_GEN, O_API, M_NEUTRAL | G2 | `GENERATE_API_TEST` |
| 查找测试用例 | V_QRY, O_TC, M_NEUTRAL | Q1 | `QUERY_TESTCASE` |
| 执行测试 | V_EXE, ∅, M_NEUTRAL | E1 | `EXECUTE_TEST` |
| 如何生成PRD | V_GEN, O_PRD, M_INTERROGATIVE | Q4 | `QUERY_KNOWLEDGE` |
| 帮我生成UI测试 | V_GEN, O_UI, M_IMPERATIVE | G1 | `GENERATE_UI_TEST` |
| 怎么用 | V_HELP, ∅, M_HELP | H1 | `HELP` |
| 测试 | ∅, ∅, M_NEUTRAL | F1 | `CHAT` |

## 边界处理

### 词长优先匹配

解决 "怎么用" 和 "怎么" 的前缀重叠问题：

```
"怎么用" → M_HELP（3字符，优先匹配）
"怎么测试" → M_INTERROGATIVE（"怎么" 2字符）
```

### 特异度过滤

命中特定类型时移除通用类型：

```
"接口测试用例" → O_API（移除 O_TC）
"UI测试用例" → O_UI（移除 O_TC）
```

### 语义模糊输入

```
"测试" → CHAT（score=0，不触发 LLM fallback）
```

## API 参考

### IntentClassifier

```python
class IntentClassifier:
    def classify(message: str) -> str
        """简单分类，返回意图字符串"""
    
    def classify_with_details(message: str) -> ClassificationResult
        """详细分类，返回完整结果"""
    
    async def classify_with_llm(message: str, llm_service) -> Dict
        """带 LLM fallback 的异步分类"""
    
    def get_entities(message: str) -> Dict
        """提取实体（URL、API端点等）"""
    
    def classify_with_context(message: str, context: Dict) -> str
        """带上下文的分类"""
```

### ClassificationResult

```python
@dataclass
class ClassificationResult:
    intent: str          # 意图类型
    score: float         # 命中强度（0.0-1.0）
    method: str          # 分类方法（rule/llm）
    rule_id: str         # 规则ID（G1, Q4, F1）
    reasoning: str       # 判断理由
    triple: Triple       # 提取的三元组
    entities: Dict       # 实体
    skill_to_use: str    # 推荐的 skill
```

## 测试

```bash
# 运行意图分类测试
pytest tests/core/agents/intent/test_intent_classifier.py -v

# 运行覆盖率测试
pytest tests/core/agents/intent/ --cov=core/agents/intent
```

## 设计文档

详细设计文档：`D:\Demo\docs\intent_classification_design.md`

## 变更历史

### v2.0 (2026-03-25)

- 重构为基于集合论的三维模型 (V, O, M)
- 新增语气维度 M，解决疑问句歧义
- 优化特异度过滤逻辑
- 添加 LLM fallback 触发条件
- 完善边界 case 处理

### v1.0

- 初始版本，关键词匹配实现