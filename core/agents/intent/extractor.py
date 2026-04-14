"""
意图分类系统 - 三元组提取器

从用户消息中提取 三元组，不承担优先级裁决职责。

设计原则：
1. 提取器只负责"找到什么"，不负责"选哪个"
2. 对象集合按特异度过滤（命中特定类型时移除通用类型）
3. 语气提取按词长降序排序，确保长词优先匹配

关键实现：
- 词长排序：确保 "怎么用" 先于 "怎么" 被检查
- 特异度过滤：命中 O_UI 或 O_API 时，移除 O_TC
- 多动词支持：verbs 为集合，允许命中多个

Author: Intent Classification System
Version: 2.0
"""

import logging
from typing import Dict, List, Set, Optional

from .sets import IntentSets, INTENT_SETS
from .types import Triple, VerbSet, ObjectSet, ModalitySet

logger = logging.getLogger(__name__)


class TripleExtractor:
    """
    三元组提取器
    
    职责：从消息中提取语义单元，不进行意图推导
    
    Example:
        extractor = TripleExtractor(sets)
        triple = extractor.extract("帮我生成接口测试用例")
        # Triple(verbs={V_GEN}, objects=[O_API], modality=M_IMPERATIVE)
    """
    
    def __init__(self, sets: Optional[IntentSets] = None):
        """
        初始化提取器
        
        Args:
            sets: 集合定义，默认使用全局单例 INTENT_SETS
        """
        self._sets = sets or INTENT_SETS
        
        # 预处理：按词长降序排序所有关键词，用于提取
        self._sorted_v_gen = sorted(self._sets.V_GEN, key=len, reverse=True)
        self._sorted_v_qry = sorted(self._sets.V_QRY, key=len, reverse=True)
        self._sorted_v_exe = sorted(self._sets.V_EXE, key=len, reverse=True)
        self._sorted_v_help = sorted(self._sets.V_HELP, key=len, reverse=True)
        
        self._sorted_o_ui = sorted(self._sets.O_UI, key=len, reverse=True)
        self._sorted_o_api = sorted(self._sets.O_API, key=len, reverse=True)
        self._sorted_o_tc = sorted(self._sets.O_TC, key=len, reverse=True)
        self._sorted_o_know = sorted(self._sets.O_KNOW, key=len, reverse=True)
        self._sorted_o_prd = sorted(self._sets.O_PRD, key=len, reverse=True)
        
        self._sorted_m_interrogative = sorted(self._sets.M_INTERROGATIVE, key=len, reverse=True)
        self._sorted_m_imperative = sorted(self._sets.M_IMPERATIVE, key=len, reverse=True)
    
    def extract(self, message: str) -> Triple:
        """
        从消息中提取三元组
        
        Args:
            message: 用户输入的消息
            
        Returns:
            Triple 对象，包含 verbs、objects、modality 和 matched_tokens
        """
        if not message or not message.strip():
            return Triple()
        
        message_lower = message.lower()
        
        # Step 1: 提取动词（多值）
        verbs, verb_tokens = self._extract_verbs(message_lower)
        
        # Step 2: 提取对象（多值，按特异度过滤）
        objects, object_tokens = self._extract_objects(message_lower)
        
        # Step 3: 提取语气（单值）
        modality, modality_tokens = self._extract_modality(message_lower)
        
        # 构建 matched_tokens 用于调试
        matched_tokens = {
            "verbs": verb_tokens,
            "objects": object_tokens,
            "modality": modality_tokens
        }
        
        triple = Triple(
            verbs=frozenset(verbs),
            objects=objects,
            modality=modality,
            matched_tokens=matched_tokens
        )
        
        logger.debug(f"[Extractor] Triple extracted: {triple}")
        return triple
    
    def _extract_verbs(self, message_lower: str) -> tuple:
        """
        提取动词集合标签
        
        Args:
            message_lower: 小写化的消息
            
        Returns:
            (verbs_set, matched_tokens)
        """
        verbs: Set[str] = set()
        matched: List[str] = []
        
        # 检查 V_GEN（生成动作）
        for kw in self._sorted_v_gen:
            if kw in message_lower:
                verbs.add(VerbSet.GEN)
                matched.append(kw)
                break  # 每个集合只匹配一个关键词
        
        # 检查 V_QRY（查询动作）
        for kw in self._sorted_v_qry:
            if kw in message_lower:
                verbs.add(VerbSet.QRY)
                matched.append(kw)
                break
        
        # 检查 V_EXE（执行动作）
        for kw in self._sorted_v_exe:
            if kw in message_lower:
                verbs.add(VerbSet.EXE)
                matched.append(kw)
                break
        
        # 检查 V_HELP（帮助动作）
        for kw in self._sorted_v_help:
            if kw in message_lower:
                verbs.add(VerbSet.HELP)
                matched.append(kw)
                break
        
        return verbs, matched
    
    def _extract_objects(self, message_lower: str) -> tuple:
        """
        提取对象集合标签（按特异度排序和过滤）
        
        特异度过滤规则：
        - 如果命中 O_UI 或 O_API（特定类型），则移除 O_TC（通用类型）
        - 因为 O_UI, O_API ⊂ O_TC_GENERAL，特定类型已经蕴含了通用类型
        
        Args:
            message_lower: 小写化的消息
            
        Returns:
            (objects_list, matched_tokens)
        """
        objects: List[str] = []
        matched: List[str] = []
        
        # 按特异度顺序检查：UI > API > TC > PRD > KNOW
        # 特异性高的在前，确保优先匹配
        
        # 检查 O_UI（UI测试，特异度高）
        for kw in self._sorted_o_ui:
            if kw in message_lower:
                objects.append(ObjectSet.UI)
                matched.append(kw)
                break
        
        # 检查 O_API（接口测试，特异度高）
        for kw in self._sorted_o_api:
            if kw in message_lower:
                objects.append(ObjectSet.API)
                matched.append(kw)
                break
        
        # 检查 O_TC（通用测试用例，特异度中）
        # 注意：如果已经命中 O_UI 或 O_API，则不再添加 O_TC
        has_specific = ObjectSet.UI in objects or ObjectSet.API in objects
        if not has_specific:
            for kw in self._sorted_o_tc:
                if kw in message_lower:
                    objects.append(ObjectSet.TC)
                    matched.append(kw)
                    break
        
        # 检查 O_PRD（PRD文档，特异度低）
        for kw in self._sorted_o_prd:
            if kw in message_lower:
                objects.append(ObjectSet.PRD)
                matched.append(kw)
                break
        
        # 检查 O_KNOW（知识库，特异度低）
        for kw in self._sorted_o_know:
            if kw in message_lower:
                objects.append(ObjectSet.KNOW)
                matched.append(kw)
                break
        
        return objects, matched
    
    def _extract_modality(self, message_lower: str) -> tuple:
        """
        提取语气模式（单值）
        
        关键实现：
        - 按词长降序排序，确保 "怎么用" 先于 "怎么" 被检查
        - frozenset 无序，必须显式排序
        - 对于前缀重叠的情况，长词优先匹配
        
        前缀重叠处理：
        - "怎么用" ∈ V_HELP → 归入帮助语气
        - "怎么" ∈ M_INTERROGATIVE → 归入疑问语气
        - 解决方案：合并所有语气词，按词长降序遍历
        
        Args:
            message_lower: 小写化的消息
            
        Returns:
            (modality_str, matched_token)
        """
        matched: List[str] = []
        
        # 构建所有语气词的列表，附带其对应的语气类型
        # 格式：(keyword, modality, source_set)
        all_modality_keywords = []
        
        # M_IMPERATIVE
        for kw in self._sets.M_IMPERATIVE:
            all_modality_keywords.append((kw, ModalitySet.IMPERATIVE))
        
        # M_INTERROGATIVE
        for kw in self._sets.M_INTERROGATIVE:
            all_modality_keywords.append((kw, ModalitySet.INTERROGATIVE))
        
        # V_HELP（"怎么用" 等归入帮助语气）
        for kw in self._sets.V_HELP:
            all_modality_keywords.append((kw, ModalitySet.HELP))
        
        # 按词长降序排序，确保长词优先匹配
        # "怎么用"（3字符）> "怎么"（2字符）
        all_modality_keywords.sort(key=lambda x: len(x[0]), reverse=True)
        
        # 遍历所有关键词，第一个匹配的即为结果
        for kw, modality in all_modality_keywords:
            if kw in message_lower:
                matched.append(kw)
                return modality, matched
        
        # 默认中性模式
        return ModalitySet.NEUTRAL, matched
    
    def extract_entities(self, message: str) -> Dict[str, str]:
        """
        提取实体（URL、API端点、HTTP方法、脚本名称等）
        
        这是辅助方法，用于从消息中提取结构化信息。
        
        Args:
            message: 用户消息
            
        Returns:
            实体字典，如 {"url": "https://example.com", "method": "POST", "script_name": "login_test.py"}
        """
        import re
        
        entities = {}
        remaining_message = message
        
        script_pattern = r'([a-zA-Z0-9_\-\u4e00-\u9fa5./]+\.(py|js|ts|spec\.js|test\.js|robot))'
        script_match = re.search(script_pattern, remaining_message, re.IGNORECASE)
        if script_match:
            script_name = script_match.group(1)
            if '\n' not in script_name and '\r' not in script_name:
                entities["script_name"] = script_name
                remaining_message = remaining_message.replace(script_name, " ")
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        url_match = re.search(url_pattern, remaining_message)
        if url_match:
            entities["url"] = url_match.group()
            remaining_message = remaining_message.replace(url_match.group(), " ")
        
        endpoint_pattern = r'(?:/api/[^\s]+|https?://[^\s]+/api/[^\s]+)'
        endpoint_match = re.search(endpoint_pattern, remaining_message)
        if endpoint_match:
            entities["api_endpoint"] = endpoint_match.group()
        
        http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        remaining_upper = remaining_message.upper()
        for method in http_methods:
            if method in remaining_upper:
                entities["http_method"] = method
                break
        
        id_pattern = r'(?:测试|用例|case|test)?[ Id]*(\d+)'
        id_match = re.search(id_pattern, remaining_message, re.IGNORECASE)
        if id_match:
            entities["test_id"] = id_match.group(1)
        
        element_patterns = [
            r'(按钮|button|输入框|input|链接|link|复选框|checkbox)',
            r'(登录按钮|注册按钮|提交按钮|submit|取消|cancel)',
        ]
        for pattern in element_patterns:
            element_match = re.search(pattern, remaining_message, re.IGNORECASE)
            if element_match:
                entities["page_element"] = element_match.group()
                break
        
        return entities