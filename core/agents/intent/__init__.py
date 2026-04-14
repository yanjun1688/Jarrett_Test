"""
意图分类系统

基于集合论 + 谓词逻辑的形式化规范实现的意图分类模块。

核心概念：
- 三维模型：动作(V) + 对象(O) + 语气(M)
- 推导规则：从三元组推导意图
- 规则优先，LLM 兜底

主要组件：
- IntentClassifier: 分类器主类
- IntentSets: 集合定义
- TripleExtractor: 三元组提取器
- derive_intent: 推导规则函数

使用示例：
    from core.agents.intent import IntentClassifier
    
    classifier = IntentClassifier()
    
    # 简单分类
    intent = classifier.classify("生成测试用例")
    
    # 详细分类
    result = classifier.classify_with_details("生成测试用例")
    print(result.intent)    # "generate_testcase"
    print(result.rule_id)   # "G3"
    print(result.score)     # 1.0
    
    # 带 LLM fallback
    result = await classifier.classify_with_llm("帮我分析这段代码", llm_service)

设计文档：D:\\Demo\\docs\\intent_classification_design.md
"""

from .types import (
    Triple,
    ClassificationResult,
    VerbSet,
    ObjectSet,
    ModalitySet,
    VERB_PRIORITY,
    OBJECT_SPECIFICITY,
)
from .sets import IntentSets, INTENT_SETS
from .extractor import TripleExtractor
from .rules import derive_intent
from .classifier import IntentClassifier

__all__ = [
    # 主类
    "IntentClassifier",
    
    # 数据类型
    "Triple",
    "ClassificationResult",
    
    # 枚举
    "VerbSet",
    "ObjectSet",
    "ModalitySet",
    
    # 集合定义
    "IntentSets",
    "INTENT_SETS",
    
    # 提取器
    "TripleExtractor",
    
    # 规则
    "derive_intent",
    
    # 常量
    "VERB_PRIORITY",
    "OBJECT_SPECIFICITY",
]