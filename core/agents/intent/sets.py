"""
意图分类系统 - 集合定义

基于集合论的形式化规范，定义三维模型 (V, O, M) 的基础集合。

设计原则：
1. 动词集合 V: V_gen ∪ V_qry ∪ V_exe ∪ V_help，且任意 Vᵢ ∩ Vⱼ = ∅
2. 对象集合 O: 叶子层互不相交，通过特异度原则解决包含关系
3. 语气集合 M: M_interrogative ∪ M_imperative ∪ M_neutral，且任意 Mᵢ ∩ Mⱼ = ∅

注意：
- "测试" 不加入任何集合，保持语义纯洁性（单独出现时返回 CHAT）
- "怎么用" 和 "怎么" 存在前缀重叠，通过词长排序解决

Reference: D:\\Demo\\docs\\intent_classification_design.md
Author: Intent Classification System
Version: 2.0
"""

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class IntentSets:
    """
    基于集合论的意图定义——三维模型 (V, O, M)
    
    使用 frozen=True 保证不可变性，避免运行时被意外修改。
    使用 FrozenSet 保证集合内容的不可变性。
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 动作集合 V（严格互不相交）
    # ═══════════════════════════════════════════════════════════════
    
    V_GEN: FrozenSet[str] = frozenset({
        "生成", "创建", "编写", "设计", "帮我写", "给我生成", "新建", "起草",
        "写", "编", "搞"
    })
    """
    生成/创作动作集合
    
    关键词：生成、创建、编写、设计、帮我写、给我生成、新建、起草
    
    注意：
    - "做" 已移除，因为语义过于模糊（"能做什么"、"做什么" 不应触发生成意图）
    - 单独的 "做" 字容易误判，用户真正需要生成时会使用更明确的词
    
    Example:
        "生成测试用例" → V_GEN 命中 "生成"
        "帮我写一个登录测试" → V_GEN 命中 "帮我写"
    """
    
    V_QRY: FrozenSet[str] = frozenset({
        "查找", "查询", "看看", "显示", "列出", "找到", "查看", "搜索",
        "已有", "已存在", "现有的", "项目里", "有没有", "存在"
    })
    """
    查询/检索动作集合
    
    关键词：查找、查询、看看、显示、列出、找到、查看、搜索、已有
    
    Example:
        "查找测试用例" → V_QRY 命中 "查找"
        "项目里有没有登录测试" → V_QRY 命中 "项目里"、"有没有"
    """
    
    V_EXE: FrozenSet[str] = frozenset({
        "执行", "运行", "开始", "跑一下", "启动", "跑", "启动测试"
    })
    """
    执行/运行动作集合
    
    关键词：执行、运行、开始、跑一下、启动
    
    注意：
    - "测试" 不加入此集合（语义模糊，单独出现时返回 CHAT）
    - E1 规则放宽：对象为空时也允许触发（"执行"本身语义完整）
    
    Example:
        "执行测试" → V_EXE 命中 "执行"
        "跑一下" → V_EXE 命中 "跑一下"
    """
    
    V_HELP: FrozenSet[str] = frozenset({
        "帮助", "怎么用", "使用说明", "帮助我", "help"
    })
    """
    帮助/说明动作集合
    
    关键词：帮助、怎么用、使用说明
    
    注意：
    - "怎么用" 与 M_INTERROGATIVE 的 "怎么" 存在前缀重叠
    - 通过词长排序确保 "怎么用" 优先匹配
    - "能做什么" 已移除，因为询问系统能力属于 CHAT，不是请求帮助
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 对象集合 O（叶子层，互不相交）
    # ═══════════════════════════════════════════════════════════════
    
    O_UI: FrozenSet[str] = frozenset({
        "ui测试", "web测试", "自动化测试", "录制测试", "网页测试",
        "前端测试", "界面测试", "浏览器测试", "selenium测试", "playwright测试"
    })
    """
    UI/Web 测试对象集合
    
    特异度：高（特定类型）
    蕴含关系：O_UI ⊂ O_TC_GENERAL
    
    Example:
        "生成UI测试" → O_UI 命中 "ui测试"
        "web测试怎么写" → O_UI 命中 "web测试"
    """
    
    O_API: FrozenSet[str] = frozenset({
        "接口测试", "api测试", "http测试", "rest测试",
        "接口", "api", "后端测试", "服务端测试"
    })
    """
    API/接口测试对象集合
    
    特异度：高（特定类型）
    蕴含关系：O_API ⊂ O_TC_GENERAL
    
    Example:
        "生成接口测试" → O_API 命中 "接口测试"
        "这个API怎么测" → O_API 命中 "api"
    """
    
    O_TC: FrozenSet[str] = frozenset({
        "测试用例", "功能测试用例", "功能用例", "测试案例",
        "test case", "testcase", "测试场景", "用例"
    })
    """
    通用测试用例对象集合
    
    特异度：中（通用表达）
    
    注意：
    - 不包含 "测试" 单独使用（语义模糊）
    - 不包含特定类型（UI、API），特定类型有独立集合
    
    Example:
        "生成测试用例" → O_TC 命中 "测试用例"
        "功能测试用例怎么写" → O_TC 命中 "功能测试用例"
    """
    
    O_KNOW: FrozenSet[str] = frozenset({
        "知识库", "最佳实践", "文档", "规范", "指南",
        "教程", "手册", "说明", "参考资料"
    })
    """
    知识库对象集合
    
    特异度：低
    
    Example:
        "知识库里有什么" → O_KNOW 命中 "知识库"
        "测试最佳实践" → O_KNOW 命中 "最佳实践"
    """
    
    O_PRD: FrozenSet[str] = frozenset({
        "prd", "PRD", "产品需求", "需求文档", "产品文档",
        "需求说明书", "产品规格", "功能需求"
    })
    """
    PRD 文档对象集合
    
    特异度：低
    
    Example:
        "查看PRD" → O_PRD 命中 "PRD"
        "产品需求文档在哪里" → O_PRD 命中 "产品需求"、"需求文档"
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 语气集合 M（互不相交）
    # ═══════════════════════════════════════════════════════════════
    
    M_INTERROGATIVE: FrozenSet[str] = frozenset({
        "如何", "怎么", "怎样", "什么是", "为什么", "有哪些",
        "示例", "怎么写", "如何做", "怎么弄", "什么", "有哪些"
    })
    """
    疑问模式集合
    
    语义：用户在询问方法、原理、示例，而非直接执行操作
    
    关键规则：
    - Q4: Generate(v) ∧ Interrogative(m) → QUERY_KNOWLEDGE
    - 例如 "如何生成PRD" → 用户想知道方法，而非直接生成
    
    Example:
        "如何生成测试用例" → M_INTERROGATIVE 命中 "如何"
        "怎么写接口测试" → M_INTERROGATIVE 命中 "怎么"、"怎么写"
    """
    
    M_IMPERATIVE: FrozenSet[str] = frozenset({
        "帮我", "给我", "请", "麻烦", "能不能帮", "帮帮我",
        "帮我一下", "麻烦帮"
    })
    """
    祈使模式集合
    
    语义：用户请求执行某个操作（语气强烈）
    
    注意：
    - "帮我生成" 中的 "帮我" 归入 M_IMPERATIVE
    - "生成" 仍归入 V_GEN
    - 三元组：verbs={V_GEN}, modality=M_IMPERATIVE
    
    Example:
        "帮我生成测试用例" → M_IMPERATIVE 命中 "帮我"
        "给我写一个登录测试" → M_IMPERATIVE 命中 "给我"
    """
    
    # ═══════════════════════════════════════════════════════════════
    # 聚合集合（由叶子集合计算，只读属性）
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def V_ALL(self) -> FrozenSet[str]:
        """所有动词集合的并集"""
        return self.V_GEN | self.V_QRY | self.V_EXE | self.V_HELP
    
    @property
    def O_TC_SPECIFIC(self) -> FrozenSet[str]:
        """
        特定类型的测试用例（UI、API）
        
        蕴含关系：O_TC_SPECIFIC ⊂ O_TC_GENERAL
        """
        return self.O_UI | self.O_API
    
    @property
    def O_TC_GENERAL(self) -> FrozenSet[str]:
        """
        所有测试相关对象的并集
        
        包含：O_TC（通用）+ O_UI（UI测试）+ O_API（接口测试）
        """
        return self.O_TC | self.O_TC_SPECIFIC
    
    @property
    def O_ALL(self) -> FrozenSet[str]:
        """所有对象集合的并集"""
        return self.O_TC_GENERAL | self.O_KNOW | self.O_PRD


# 单例实例，全局共享
INTENT_SETS = IntentSets()