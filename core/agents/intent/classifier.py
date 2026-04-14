"""
意图分类系统 - 分类器主类

核心职责：
1. 规则优先分类：基于三元组推导
2. LLM 兜底：处理模糊/复杂表达
3. 缓存优化：减少重复计算

设计原则：
1. 规则优先，LLM 兜底
2. LLM fallback 触发条件明确（消息长度 + 置信度阈值）
3. 配置在 __init__ 读取，避免热路径反复访问 settings

Author: Intent Classification System
Version: 2.0
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, TYPE_CHECKING

from django.core.cache import cache
from django.conf import settings

from .sets import IntentSets, INTENT_SETS
from .types import Triple, ClassificationResult
from .extractor import TripleExtractor
from .rules import derive_intent
from shared.constants import IntentType

if TYPE_CHECKING:
    from core.agents.llm.base_llm import BaseLLMService

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    基于集合论 + 谓词逻辑的意图分类器
    
    核心流程：
    1. 预处理消息（移除代码块）
    2. Skill 关键词优先匹配
    3. 提取三元组
    4. 规则推导意图
    5. CHAT 快速路径（跳过 LLM fallback）
    6. 动态阈值判断是否需要 LLM fallback
    7. 返回分类结果
    
    Example:
        classifier = IntentClassifier()
        result = await classifier.classify_with_llm("生成测试用例", llm_service)
        print(result.intent)  # "generate_testcase"
    """
    
    # 按意图类型的动态 confidence_threshold
    INTENT_THRESHOLDS = {
        IntentType.CHAT: 0.3,
        IntentType.GENERATE_TESTCASE: 0.6,
        IntentType.GENERATE_UI_TEST: 0.6,
        IntentType.GENERATE_API_TEST: 0.6,
        IntentType.GENERATE_PRD: 0.6,
        IntentType.QUERY_KNOWLEDGE: 0.5,
        IntentType.QUERY_TESTCASE: 0.5,
        IntentType.QUERY_PRD: 0.5,
        IntentType.EXECUTE_TEST: 0.6,
        IntentType.HELP: 0.3,
    }
    
    # CHAT 快速路径中，包含这些关键词的长消息仍走 LLM fallback
    _TOOL_KEYWORDS = frozenset({
        "测试", "生成", "执行", "查询", "安装", "skill", "技能",
        "用例", "接口", "api", "ui", "浏览器", "脚本", "知识库",
    })
    
    SKILL_MAPPING = {
        "testcase-generator": {
            "intents": [IntentType.GENERATE_TESTCASE],
            "keywords": ["测试用例", "生成测试", "测试案例", "test case", "testcase"],
            "intent_verbs": ["生成", "创建", "编写", "设计", "帮我生成", "给我生成"]
        },
        "agent-browser": {
            "intents": [IntentType.GENERATE_UI_TEST],
            "keywords": ["浏览器", "打开网页", "点击", "截图", "网页测试", "browser", "screenshot"],
            "intent_verbs": ["打开", "访问", "点击", "截图", "自动化"]
        },
        "api-design-principles": {
            "intents": [],
            "keywords": ["api设计", "接口设计", "rest api", "graphql"],
            "intent_verbs": ["设计", "帮我设计", "如何设计"]
        },
        "find-skills": {
            "intents": [],
            "keywords": ["找技能", "搜索技能", "安装技能", "find skill"],
            "intent_verbs": ["找", "搜索", "查找"]
        },
        "webapp-testing": {
            "intents": [],
            "keywords": ["web测试", "前端测试", "playwright"],
            "intent_verbs": ["测试", "运行"]
        },
        "frontend-design": {
            "intents": [],
            "keywords": ["前端设计", "ui设计", "页面设计", "landing page"],
            "intent_verbs": ["设计", "创建", "生成"]
        },
        "python-testing-patterns": {
            "intents": [],
            "keywords": ["python测试", "pytest", "单元测试"],
            "intent_verbs": ["测试", "编写", "生成"]
        }
    }
    """
    Skill 映射表（向后兼容）
    
    用于根据意图查找对应的 skill。
    
    Example:
        for skill_name, skill_config in IntentClassifier.SKILL_MAPPING.items():
            if intent in skill_config.get("intents", []):
                return skill_name
    """
    
    def __init__(self, sets: Optional[IntentSets] = None, prompt_builder: Optional[Any] = None):
        """
        初始化分类器
        
        Args:
            sets: 集合定义，默认使用全局单例 INTENT_SETS
            prompt_builder: PromptBuilder 实例（用于 LLM fallback）
        """
        self._sets = sets or INTENT_SETS
        self._extractor = TripleExtractor(self._sets)
        
        config = getattr(settings, "INTENT_CONFIG", {})
        self._fallback_len = config.get("LLM_FALLBACK_MESSAGE_LEN", 10)
        self._confidence_threshold = config.get("CONFIDENCE_THRESHOLD", 0.6)
        
        self._cache_enabled = config.get("CACHE_ENABLED", True)
        self._cache_ttl = config.get("CACHE_TTL", 300)
        
        self._llm_service: Optional["BaseLLMService"] = None
        self._prompt_builder: Optional[Any] = prompt_builder
        
        logger.debug(
            f"[IntentClassifier] Initialized with "
            f"fallback_len={self._fallback_len}, "
            f"confidence_threshold={self._confidence_threshold}, "
            f"prompt_builder={prompt_builder is not None}"
        )
    
    def set_llm_service(self, llm_service: "BaseLLMService") -> None:
        """
        设置 LLM 服务（用于 fallback）
        
        Args:
            llm_service: LLM 服务实例
        """
        self._llm_service = llm_service
    
    def set_prompt_builder(self, prompt_builder: Any) -> None:
        """
        设置 PromptBuilder 实例（用于 LLM fallback prompt 构建）
        
        Args:
            prompt_builder: PromptBuilder 实例
        """
        self._prompt_builder = prompt_builder
    
    def _skill_keyword_match(self, message: str) -> Optional[ClassificationResult]:
        """
        Skill 名称精确匹配（只匹配 skill 名称本身，不匹配通用关键词）
        
        Args:
            message: 用户消息
            
        Returns:
            ClassificationResult 或 None
        """
        msg_lower = message.lower()
        
        for skill_name, skill_config in self.SKILL_MAPPING.items():
            # 只匹配 skill 名称本身（如 "agent-browser"、"testcase-generator"）
            if skill_name in msg_lower:
                intents = skill_config.get("intents", [])
                intent = intents[0] if intents else IntentType.CHAT
                return ClassificationResult(
                    intent=intent,
                    score=0.9,
                    rule_id="SK",
                    skill_to_use=skill_name,
                    method="skill_match",
                    reasoning=f"Skill name match: {skill_name}",
                    threshold_exempt=True,
                )
        
        return None
    
    def _contains_tool_keywords(self, message: str) -> bool:
        """检查消息是否包含工具相关关键词"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in self._TOOL_KEYWORDS)
    
    def classify(self, message: str) -> str:
        """
        简单分类接口，只返回意图
        
        Args:
            message: 用户消息
            
        Returns:
            意图类型字符串
        """
        result = self.classify_with_details(message)
        return result.intent
    
    def classify_with_details(self, message: str) -> ClassificationResult:
        """
        详细分类接口，返回完整结果
        
        Args:
            message: 用户消息
            
        Returns:
            ClassificationResult 对象
        """
        if not message or not message.strip():
            return ClassificationResult(
                intent=IntentType.CHAT,
                score=0.0,
                method="rule",
                rule_id="F1",
                reasoning="Empty message",
                confidence="low",
                threshold_exempt=False
            )
        
        cleaned_message = self._preprocess_message(message)
        
        triple = self._extractor.extract(cleaned_message)
        
        intent, rule_id, score = derive_intent(triple)
        
        entities = self._extractor.extract_entities(message)
        
        skill_to_use = self._get_skill_for_intent(intent, cleaned_message)
        
        reasoning = self._build_reasoning(triple, rule_id)
        
        threshold_exempt = (rule_id == "E1")
        
        if threshold_exempt:
            confidence = "high"
        elif score >= 0.8:
            confidence = "high"
        elif score >= 0.6:
            confidence = "medium"
        else:
            confidence = "low"
        
        return ClassificationResult(
            intent=intent,
            score=score,
            method="rule",
            rule_id=rule_id,
            reasoning=reasoning,
            triple=triple,
            entities=entities,
            skill_to_use=skill_to_use,
            confidence=confidence,
            threshold_exempt=threshold_exempt
        )
    
    async def classify_with_llm(
        self,
        message: str,
        llm_service: Optional["BaseLLMService"] = None,
    ) -> Dict[str, Any]:
        """
        带有 LLM fallback 的分类接口
        
        优化流程：
        1. 检查缓存
        2. Skill 关键词优先匹配（score=0.9，直接返回）
        3. 规则分类
        4. CHAT 快速路径（短消息或无工具关键词直接返回）
        5. 动态阈值判断是否需要 LLM fallback
        
        Args:
            message: 用户消息
            llm_service: LLM 服务（可选，使用注入的服务）
            
        Returns:
            分类结果字典
        """
        logger.info(f"[Intent] 开始意图分类: {message[:50]}...")
        
        cached_result = self._get_cached_result(message)
        if cached_result:
            logger.info(f"[Intent] 缓存命中，跳过分类")
            return cached_result
        
        # Skill 关键词优先匹配
        skill_result = self._skill_keyword_match(message)
        if skill_result:
            logger.info(f"[Intent] Skill 关键词命中: {skill_result.skill_to_use} → {skill_result.intent}")
            result = skill_result.to_dict()
            self._set_cached_result(message, result)
            return result
        
        rule_result = self.classify_with_details(message)
        intent = rule_result.intent
        score = rule_result.score
        
        logger.info(
            f"[Intent] 规则分类结果: intent={intent}, "
            f"rule_id={rule_result.rule_id}, score={score:.2f}, "
            f"threshold_exempt={rule_result.threshold_exempt}"
        )
        
        llm = llm_service or self._llm_service
        should_fallback = self._should_fallback(
            intent, score, message, rule_result.threshold_exempt
        )
        
        if not should_fallback:
            result = rule_result.to_dict()
            self._set_cached_result(message, result)
            return result
        
        if llm is None:
            logger.warning(f"[Intent] 需要 LLM fallback 但无 LLM 服务")
            return rule_result.to_dict()
        
        logger.info(f"[Intent] 触发 LLM fallback: intent={intent}, score={score:.2f}")
        
        try:
            llm_result = await self._classify_with_llm_api(message, llm)
            llm_result["method"] = "llm"
            llm_result["entities"] = rule_result.entities
            
            logger.info(
                f"[Intent] LLM 结果: intent={llm_result.get('intent')}, "
                f"confidence={llm_result.get('confidence', 0):.2f}"
            )
            
            self._set_cached_result(message, llm_result)
            return llm_result
            
        except Exception as e:
            logger.error(f"[Intent] LLM fallback 失败: {e}")
            return rule_result.to_dict()
    
    def _should_fallback(
        self,
        intent: str,
        score: float,
        message: str,
        threshold_exempt: bool = False
    ) -> bool:
        """
        判断是否需要 LLM fallback（方案 D）
        
        逻辑：
        1. threshold_exempt=True → 不 fallback（如 E1 规则）
        2. 高置信度规则命中（score >= 0.6）→ 不 fallback
        3. CHAT + 高 score（F1, 0.7）→ 不 fallback（确定是闲聊）
        4. CHAT + 低 score（F1-gen/F1-qry, 0.3）→ fallback（动词无对象，需要 LLM 判断）
        """
        if threshold_exempt:
            return False
        
        # 高置信度规则命中，直接返回
        if score >= 0.6:
            return False
        
        # 低置信度，需要 LLM 判断
        return True
    
    def _preprocess_message(self, message: str) -> str:
        """
        预处理消息：移除代码块、JSON 等
        
        Args:
            message: 原始消息
            
        Returns:
            清理后的消息
        """
        import re
        
        cleaned = message
        
        # 移除代码块
        code_block_pattern = r'```[\s\S]*?```'
        cleaned = re.sub(code_block_pattern, '', cleaned)
        
        # 移除行内代码
        inline_code_pattern = r'`[^`]+`'
        cleaned = re.sub(inline_code_pattern, '', cleaned)
        
        # 移除大段 JSON
        if cleaned.count('{') > 5 or cleaned.count('"') > 20:
            json_like_pattern = r'\{[\s\S]{100,}\}'
            cleaned = re.sub(json_like_pattern, '[JSON数据]', cleaned)
        
        # 合并空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _get_skill_for_intent(self, intent: str, message: str) -> Optional[str]:
        """
        根据意图和消息内容推荐 skill
        
        Args:
            intent: 意图类型
            message: 消息内容
            
        Returns:
            skill 名称或 None
        """
        skill_mapping = {
            IntentType.GENERATE_TESTCASE: "testcase-generator",
            IntentType.GENERATE_UI_TEST: "agent-browser",
            IntentType.GENERATE_API_TEST: "api-design-principles",
        }
        
        return skill_mapping.get(intent)
    
    def _build_reasoning(self, triple: Triple, rule_id: str) -> str:
        """
        构建分类理由说明
        
        Args:
            triple: 三元组
            rule_id: 规则ID
            
        Returns:
            理由字符串
        """
        parts = [f"Rule: {rule_id}"]
        
        if triple.matched_tokens:
            verbs = triple.matched_tokens.get("verbs", [])
            objects = triple.matched_tokens.get("objects", [])
            if verbs:
                parts.append(f"Verbs: {', '.join(verbs)}")
            if objects:
                parts.append(f"Objects: {', '.join(objects)}")
        
        return " | ".join(parts)
    
    async def _classify_with_llm_api(
            self,
            message: str,
            llm_service: "BaseLLMService"
        ) -> Dict[str, Any]:
            """
            使用 LLM 进行意图分类
        
            Args:
                message: 用户消息
                llm_service: LLM 服务实例
            
            Returns:
                分类结果字典
            """
            cleaned_message = self._preprocess_message(message)
        
            if self._prompt_builder:
                prompts = self._prompt_builder.build_for_intent_classification(cleaned_message)
                system_message = prompts["system_prompt"]
                user_prompt = prompts["user_prompt"]
            else:
                system_message = "意图分类器。只返回JSON。"
                user_prompt = """判断用户意图，从以下选项中选一个：
chat, generate_testcase, generate_ui_test, generate_api_test, query_knowledge, query_testcase, execute_test, help

用户消息：{}

回复格式：{{"intent":"<意图>","confidence":0.8}}""".format(cleaned_message)
        
            try:
                response = await llm_service.generate(
                    prompt=user_prompt,
                    system_message=system_message
                )
            
                if response is None:
                    logger.error("[Intent] LLM returned None")
                    return {
                        "intent": IntentType.CHAT,
                        "confidence": 0.5,
                        "reasoning": "LLM returned None"
                    }
            
                if not isinstance(response, str):
                    logger.error(f"[Intent] LLM returned non-string type: {type(response)}")
                    return {
                        "intent": IntentType.CHAT,
                        "confidence": 0.5,
                        "reasoning": f"LLM returned non-string: {type(response).__name__}"
                    }
            
                response_text = response.strip()
                if response_text.startswith("```"):
                    lines = response_text.split("\n")
                    response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
                result = json.loads(response_text)
            
                valid_intents = [
                    IntentType.CHAT,
                    IntentType.GENERATE_UI_TEST,
                    IntentType.GENERATE_API_TEST,
                    IntentType.GENERATE_TESTCASE,
                    IntentType.QUERY_KNOWLEDGE,
                    IntentType.QUERY_TESTCASE,
                    IntentType.EXECUTE_TEST,
                    IntentType.HELP
                ]
            
                if result.get("intent") not in valid_intents:
                    result["intent"] = IntentType.CHAT
            
                return result
            
            except json.JSONDecodeError as e:
                logger.error(f"[Intent] LLM 响应解析失败: {e}")
                return {
                    "intent": IntentType.CHAT,
                    "confidence": 0.5,
                    "reasoning": "Failed to parse LLM response"
                }
    
    # ═══════════════════════════════════════════════════════════════
    # 缓存方法
    # ═══════════════════════════════════════════════════════════════
    
    def _get_cache_key(self, message: str) -> str:
        """生成缓存 key"""
        normalized = message.strip().lower()
        hash_val = hashlib.md5(normalized.encode()).hexdigest()[:16]
        return f"intent:{hash_val}"
    
    def _get_cached_result(self, message: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        if not self._cache_enabled:
            return None
        try:
            cache_key = self._get_cache_key(message)
            return cache.get(cache_key)
        except Exception as e:
            logger.warning(f"[Intent] 缓存读取失败: {e}")
            return None
    
    def _set_cached_result(self, message: str, result: Dict[str, Any]) -> None:
        """设置缓存结果"""
        if not self._cache_enabled:
            return
        try:
            cache_key = self._get_cache_key(message)
            cache.set(cache_key, result, timeout=self._cache_ttl)
        except Exception as e:
            logger.warning(f"[Intent] 缓存写入失败: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # 兼容旧接口
    # ═══════════════════════════════════════════════════════════════
    
    def get_entities(self, message: str) -> Dict[str, Any]:
        """
        提取实体（兼容旧接口）
        
        Args:
            message: 用户消息
            
        Returns:
            实体字典
        """
        return self._extractor.extract_entities(message)
    
    def classify_with_context(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        带上下文的分类（兼容旧接口）
        
        Args:
            message: 用户消息
            context: 对话上下文
            
        Returns:
            意图类型
        """
        intent = self.classify(message)
        
        if context:
            last_intent = context.get("last_intent")
            if intent == IntentType.CHAT and last_intent:
                continue_keywords = ["再", "继续", "还有", "另外", "再增加", "改成", "修改"]
                if any(kw in message for kw in continue_keywords):
                    return last_intent
            
            test_type = context.get("test_type")
            if test_type == "api" and intent == IntentType.GENERATE_UI_TEST:
                return IntentType.GENERATE_API_TEST
            elif test_type == "ui" and intent == IntentType.GENERATE_API_TEST:
                return IntentType.GENERATE_UI_TEST
        
        return intent