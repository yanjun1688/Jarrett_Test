"""
意图分类系统 - 类型定义

基于集合论 + 谓词逻辑的形式化规范，定义核心数据类型和常量。

设计原则：
1. 三维模型：动作(V) + 对象(O) + 语气(M)
2. 动词集合互不相交，保证推导无歧义
3. 对象集合按特异度分层，特定类型优先匹配

Author: Intent Classification System
Version: 2.0
"""

from dataclasses import dataclass, field
from typing import FrozenSet, List, Dict, Any, Optional
from enum import Enum


class VerbSet(str, Enum):
    """动词集合标签（互不相交）"""
    GEN = "V_GEN"      # 生成/创作动作
    QRY = "V_QRY"      # 查询/检索动作
    EXE = "V_EXE"      # 执行/运行动作
    HELP = "V_HELP"    # 帮助/说明动作


class ObjectSet(str, Enum):
    """对象集合标签（叶子层，互不相交）"""
    UI = "O_UI"        # UI/Web 测试
    API = "O_API"      # API/接口测试
    TC = "O_TC"        # 通用测试用例
    KNOW = "O_KNOW"    # 知识库
    PRD = "O_PRD"      # PRD 文档


class ModalitySet(str, Enum):
    """语气模式集合标签（互不相交）"""
    INTERROGATIVE = "M_INTERROGATIVE"  # 疑问模式
    IMPERATIVE = "M_IMPERATIVE"        # 祈使模式
    NEUTRAL = "M_NEUTRAL"              # 中性模式
    HELP = "M_HELP"                    # 帮助模式（V_HELP 的语气化）


@dataclass
class Triple:
    """
    三元组：从用户消息中提取的语义单元
    
    Attributes:
        verbs: 匹配到的动词集合标签，可能命中多个（如 {V_GEN, V_QRY}）
        objects: 匹配到的对象集合标签，按特异度排序（特定类型在前）
        modality: 语气模式标签，唯一值
        matched_tokens: 用于调试的原始匹配词
        
    Example:
        Triple(
            verbs={V_GEN},
            objects=[O_TC],
            modality=M_NEUTRAL,
            matched_tokens={"verbs": ["生成"], "objects": ["测试用例"]}
        )
    """
    verbs: FrozenSet[str] = field(default_factory=frozenset)
    objects: List[str] = field(default_factory=list)
    modality: str = ModalitySet.NEUTRAL
    matched_tokens: Dict[str, List[str]] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"Triple(verbs={set(self.verbs)}, objects={self.objects}, modality={self.modality})"


@dataclass
class ClassificationResult:
    """
    分类结果
    
    Attributes:
        intent: 意图类型
        score: 命中强度（0.0-1.0），非概率，表示三元组完整度
        method: 分类方法（rule/llm/hybrid）
        rule_id: 触发的规则ID（如 G1, Q4, F1）
        reasoning: 判断理由
        triple: 提取的三元组
        entities: 提取的实体
        skill_to_use: 推荐使用的 skill
        confidence: 置信度等级（high/medium/low）
        threshold_exempt: 是否豁免阈值检查（E1规则专用）
    """
    intent: str
    score: float = 0.0
    method: str = "rule"
    rule_id: str = ""
    reasoning: str = ""
    triple: Optional[Triple] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    skill_to_use: Optional[str] = None
    confidence: str = "medium"
    threshold_exempt: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "intent": self.intent,
            "score": self.score,
            "method": self.method,
            "rule_id": self.rule_id,
            "reasoning": self.reasoning,
            "entities": self.entities,
            "skill_to_use": self.skill_to_use,
            "confidence": self.confidence,
            "threshold_exempt": self.threshold_exempt,
        }


VERB_PRIORITY = [VerbSet.EXE, VerbSet.GEN, VerbSet.QRY, VerbSet.HELP]
"""
动词优先级（用于多动词冲突裁决）

优先级顺序：执行 > 生成 > 查询 > 帮助

Example:
    "帮我查找并生成测试用例" → verbs = {V_QRY, V_GEN}
    按优先级选择 V_GEN → GENERATE_TESTCASE
"""

OBJECT_SPECIFICITY = [ObjectSet.UI, ObjectSet.API, ObjectSet.TC, ObjectSet.PRD, ObjectSet.KNOW]
"""
对象特异度顺序（用于排序和匹配优先级）

特定类型在前（UI, API），通用类型在后（TC, PRD, KNOW）
"""

EMPTY_TRIPLE = Triple()
"""空三元组，用于默认值"""