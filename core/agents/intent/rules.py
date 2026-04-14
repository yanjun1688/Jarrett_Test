"""
意图分类系统 - 推导规则

基于谓词逻辑的意图推导规则实现。

推导规则优先级：
- 语气优先检查（Q4）：最高优先级，处理 "如何生成..." 等疑问句
- 生成类（G1-G4）：按特异度顺序，特定类型（UI、API）优先于通用类型（TC）
- 执行类（E1）：对象可选，"执行" 本身语义完整
- 查询类（Q1-Q3）：需要查询动词或对象
- 帮助类（H1）：识别帮助意图
- 兜底（F1）：返回 CHAT

设计原则：
1. 动词优先级裁决在推导阶段进行，不在提取阶段
2. E1 规则放宽：Execute(v) 即可触发，不强制要求对象
3. 规则返回 包含 score，便于后续置信度判断

Author: Intent Classification System
Version: 2.0
"""

import logging
from typing import Tuple, Optional

from .types import Triple, VerbSet, ObjectSet, ModalitySet, VERB_PRIORITY
from shared.constants import IntentType

logger = logging.getLogger(__name__)


def derive_intent(triple: Triple) -> Tuple[str, str, float]:
    """
    根据推导规则从三元组推导意图
    
    推导顺序（按优先级）：
    1. 语气优先检查（Q4）- 疑问模式兜底
    2. 生成类（G1-G4）- 按对象特异度顺序
    3. 执行类（E1）- 对象可选
    4. 查询类（Q1-Q3）- 需要动词或对象
    5. 帮助类（H1）
    6. 兜底（F1）
    
    Args:
        triple: 提取的三元组
        
    Returns:
        (intent, rule_id, score)
        - intent: 意图类型字符串
        - rule_id: 触发的规则ID（如 "G1", "Q4", "F1"）
        - score: 命中强度（0.0-1.0），表示三元组完整度
        
    Example:
        >>> triple = Triple(verbs={VerbSet.GEN}, objects=[ObjectSet.TC], modality=ModalitySet.NEUTRAL)
        >>> derive_intent(triple)
        ('generate_testcase', 'G3', 1.0)
    """
    
    # ═══════════════════════════════════════════════════════════════
    # Step 1: 动词优先级裁决
    # ═══════════════════════════════════════════════════════════════
    
    primary_verb = _select_primary_verb(triple.verbs)
    
    # ═══════════════════════════════════════════════════════════════
    # Step 2: 语气优先检查（Q4 收紧版）
    # ═══════════════════════════════════════════════════════════════
    
    # 帮助语气特殊处理（最高优先级）
    if triple.modality == ModalitySet.HELP:
        logger.debug(f"[Rule H1] Help modality → HELP")
        return (IntentType.HELP, "H1", 0.8)
    
    # Q4 收紧规则：
    # 1. 疑问句 + 知识库对象 → QUERY_KNOWLEDGE
    # 2. 疑问句 + 无动词 + 有对象 → CHAT（让 LLM 解释，如 "什么是PRD"）
    # 3. 疑问句 + 有动词 + 有对象 → 继续走后续规则（按动词+对象处理）
    # 4. 疑问句 + 无动词无对象 → CHAT（让 LLM 回答）
    if triple.modality == ModalitySet.INTERROGATIVE:
        # Q4-1: Interrogative + 知识库对象 → QUERY_KNOWLEDGE
        if ObjectSet.KNOW in triple.objects:
            logger.debug(f"[Rule Q4-1] Interrogative + Knowledge object → QUERY_KNOWLEDGE")
            return (IntentType.QUERY_KNOWLEDGE, "Q4-1", 0.8)
        
        # Q4-2: Interrogative + 无动词 + 有对象 → CHAT（让 LLM 解释概念）
        if not triple.verbs and triple.objects:
            logger.debug(f"[Rule F1] Interrogative without verb but has object → CHAT")
            return (IntentType.CHAT, "F1", 0.7)
        
        # Q4-3: Interrogative + 无动词无对象 → CHAT（纯疑问句）
        if not triple.verbs and not triple.objects:
            logger.debug(f"[Rule F1] Interrogative without action → CHAT")
            return (IntentType.CHAT, "F1", 0.7)
        
        # Q4-4: Interrogative + 有动词有对象 → 继续走后续规则
        # 不在这里返回，让后续规则处理
    
    # ═══════════════════════════════════════════════════════════════
    # Step 3: 生成类意图（G1-G4）
    # 按对象特异度顺序：O_UI > O_API > O_TC > O_PRD
    # ═══════════════════════════════════════════════════════════════
    
    if primary_verb == VerbSet.GEN:
        score = _calculate_score(triple)
        
        # G1: Generate(v) ∧ IsUITest(o) ∧ ¬Interrogative(m)
        if ObjectSet.UI in triple.objects:
            logger.debug(f"[Rule G1] Generate + UI → GENERATE_UI_TEST")
            return (IntentType.GENERATE_UI_TEST, "G1", score)
        
        # G2: Generate(v) ∧ IsAPITest(o) ∧ ¬Interrogative(m)
        if ObjectSet.API in triple.objects:
            logger.debug(f"[Rule G2] Generate + API → GENERATE_API_TEST")
            return (IntentType.GENERATE_API_TEST, "G2", score)
        
        # G3: Generate(v) ∧ IsGenericTest(o) ∧ ¬IsSpecificTest(o)
        if ObjectSet.TC in triple.objects:
            logger.debug(f"[Rule G3] Generate + TC → GENERATE_TESTCASE")
            return (IntentType.GENERATE_TESTCASE, "G3", score)
        
        # G4: Generate(v) ∧ IsPRD(o)
        if ObjectSet.PRD in triple.objects:
            logger.debug(f"[Rule G4] Generate + PRD → GENERATE_PRD")
            return (IntentType.GENERATE_PRD, "G4", score)
        
        # 有生成动词但无对象 → 不确定，标记为需要 LLM 判断
        logger.debug(f"[Rule F1] Generate without object → CHAT (needs LLM)")
        return (IntentType.CHAT, "F1-gen", 0.3)
    
    # ═══════════════════════════════════════════════════════════════
    # Step 4: 执行类意图（E1）
    # 对象可选，"执行" 本身语义完整
    # ═══════════════════════════════════════════════════════════════
    
    if primary_verb == VerbSet.EXE:
        score = _calculate_score(triple)
        logger.debug(f"[Rule E1] Execute → EXECUTE_TEST")
        return (IntentType.EXECUTE_TEST, "E1", score)
    
    # ═══════════════════════════════════════════════════════════════
    # Step 5: 查询类意图（Q1-Q3）
    # 需要查询动词或对象存在
    # ═══════════════════════════════════════════════════════════════
    
    if primary_verb == VerbSet.QRY or (not primary_verb and triple.objects):
        score = _calculate_score(triple)
        
        # Q1: Query(v) ∧ IsAnyTest(o)
        if ObjectSet.UI in triple.objects or ObjectSet.API in triple.objects or ObjectSet.TC in triple.objects:
            logger.debug(f"[Rule Q1] Query + Test object → QUERY_TESTCASE")
            return (IntentType.QUERY_TESTCASE, "Q1", score)
        
        # Q2: Query(v) ∧ IsPRD(o)
        if ObjectSet.PRD in triple.objects:
            logger.debug(f"[Rule Q2] Query + PRD → QUERY_PRD")
            return (IntentType.QUERY_PRD, "Q2", score)
        
        # Q3: Query(v) ∧ IsKnowledge(o)
        if ObjectSet.KNOW in triple.objects:
            logger.debug(f"[Rule Q3] Query + Knowledge → QUERY_KNOWLEDGE")
            return (IntentType.QUERY_KNOWLEDGE, "Q3", score)
        
        # 有查询动词但无对象 → 不确定，标记为需要 LLM 判断
        if primary_verb == VerbSet.QRY:
            logger.debug(f"[Rule F1] Query without object → CHAT (needs LLM)")
            return (IntentType.CHAT, "F1-qry", 0.3)
    
    # ═══════════════════════════════════════════════════════════════
    # Step 6: 帮助类意图（H1）
    # ═══════════════════════════════════════════════════════════════
    
    if primary_verb == VerbSet.HELP:
        logger.debug(f"[Rule H1] Help verb → HELP")
        return (IntentType.HELP, "H1", 0.8)
    
    # ═══════════════════════════════════════════════════════════════
    # Step 7: 兜底（F1）
    # ═══════════════════════════════════════════════════════════════
    
    logger.debug(f"[Rule F1] Fallback → CHAT")
    return (IntentType.CHAT, "F1", 0.7)


def _select_primary_verb(verbs: frozenset) -> Optional[str]:
    """
    动词优先级裁决
    
    当 verbs 包含多个动词时，按优先级选择最高的：
    EXE > GEN > QRY > HELP
    
    Args:
        verbs: 动词集合标签
        
    Returns:
        优先级最高的动词标签，或 None
        
    Example:
        >>> _select_primary_verb({VerbSet.GEN, VerbSet.QRY})
        VerbSet.GEN  # GEN 优先级高于 QRY
    """
    for v in VERB_PRIORITY:
        if v in verbs:
            return v
    return None


def _calculate_score(triple: Triple) -> float:
    """
    计算命中强度
    
    命中强度 = 维度命中数 / 3
    - verb 命中：+0.4
    - object 命中：+0.4
    - modality 非中性：+0.2
    
    满分 1.0 = 三维度全部命中
    
    注意：score 不是概率，而是三元组完整度的度量
    
    Args:
        triple: 三元组
        
    Returns:
        命中强度（0.0-1.0）
    """
    score = 0.0
    
    if triple.verbs:
        score += 0.4
    
    if triple.objects:
        score += 0.4
    
    if triple.modality != ModalitySet.NEUTRAL:
        score += 0.2
    
    return score


# ═══════════════════════════════════════════════════════════════════
# 规则文档（供参考）
# ═══════════════════════════════════════════════════════════════════

RULES_DOCUMENTATION = """
意图推导规则形式化定义

一、生成类意图（G1-G4）
────────────────────────────────────────────────────────────────────
G1: Intent = GENERATE_UI_TEST
    ⟺ Generate(v) ∧ IsUITest(o) ∧ ¬Interrogative(m)

G2: Intent = GENERATE_API_TEST
    ⟺ Generate(v) ∧ IsAPITest(o) ∧ ¬Interrogative(m)

G3: Intent = GENERATE_TESTCASE
    ⟺ Generate(v) ∧ IsGenericTest(o) ∧ ¬IsSpecificTest(o) ∧ ¬Interrogative(m)

G4: Intent = GENERATE_PRD
    ⟺ Generate(v) ∧ IsPRD(o) ∧ ¬Interrogative(m)


二、查询类意图（Q1-Q4）
────────────────────────────────────────────────────────────────────
Q1: Intent = QUERY_TESTCASE
    ⟺ Query(v) ∧ IsAnyTest(o)

Q2: Intent = QUERY_PRD
    ⟺ Query(v) ∧ IsPRD(o)

Q3: Intent = QUERY_KNOWLEDGE
    ⟺ Query(v) ∧ IsKnowledge(o)

Q4: Intent = QUERY_KNOWLEDGE
    ⟺ AskHowTo(v, m) ∨ (Interrogative(m) ∧ ¬Query(v) ∧ ¬Execute(v))


三、执行类意图（E1）
────────────────────────────────────────────────────────────────────
E1: Intent = EXECUTE_TEST
    ⟺ Execute(v)
    
    注意：对象可选，"执行" 本身语义完整


四、帮助类意图（H1）
────────────────────────────────────────────────────────────────────
H1: Intent = HELP
    ⟺ Help(v)


五、兜底（F1）
────────────────────────────────────────────────────────────────────
F1: Intent = CHAT
    ⟺ ¬(G1 ∨ G2 ∨ G3 ∨ G4 ∨ Q1 ∨ Q2 ∨ Q3 ∨ Q4 ∨ E1 ∨ H1)
"""