"""
Token 精确计算器

使用 tiktoken 实现精确的 Token 计算，支持多种模型。

支持的模型：
- OpenAI 系列: gpt-4, gpt-3.5-turbo, gpt-4-turbo
- 智谱 GLM 系列: glm-4, glm-4-plus (估算)
- 阿里千问系列: qwen-turbo, qwen-plus (估算)
- 深度求索系列: deepseek-chat, deepseek-coder
- Anthropic 系列: claude-3 (估算)

Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
"""

import re
import logging
from typing import Dict, Optional, Any, List, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CalculationMethod(Enum):
    """Token 计算方式"""
    TIKTOKEN = "tiktoken"
    API_OR_ESTIMATE = "api_or_estimate"
    ESTIMATE = "estimate"


@dataclass
class ModelTokenConfig:
    """模型 Token 配置"""
    name: str
    tokenizer: str
    encoding: Optional[str] = None
    context_window: int = 8192
    calculation_method: CalculationMethod = CalculationMethod.TIKTOKEN
    conservative_ratio: float = 1.0


MODEL_CONFIGS: Dict[str, ModelTokenConfig] = {
    "gpt-4": ModelTokenConfig(
        name="gpt-4",
        tokenizer="tiktoken",
        encoding="cl100k_base",
        context_window=8192,
        calculation_method=CalculationMethod.TIKTOKEN,
    ),
    "gpt-4-turbo": ModelTokenConfig(
        name="gpt-4-turbo",
        tokenizer="tiktoken",
        encoding="cl100k_base",
        context_window=128000,
        calculation_method=CalculationMethod.TIKTOKEN,
    ),
    "gpt-3.5-turbo": ModelTokenConfig(
        name="gpt-3.5-turbo",
        tokenizer="tiktoken",
        encoding="cl100k_base",
        context_window=16384,
        calculation_method=CalculationMethod.TIKTOKEN,
    ),
    "glm-4": ModelTokenConfig(
        name="glm-4",
        tokenizer="glm",
        context_window=128000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "glm-4-plus": ModelTokenConfig(
        name="glm-4-plus",
        tokenizer="glm",
        context_window=128000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "glm-4-flash": ModelTokenConfig(
        name="glm-4-flash",
        tokenizer="glm",
        context_window=128000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "glm-4.7-flash": ModelTokenConfig(
        name="glm-4.7-flash",
        tokenizer="glm",
        context_window=8192,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "glm-5": ModelTokenConfig(
        name="glm-5",
        tokenizer="glm",
        context_window=4096,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "qwen-turbo": ModelTokenConfig(
        name="qwen-turbo",
        tokenizer="qwen",
        context_window=128000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.15,
    ),
    "qwen-plus": ModelTokenConfig(
        name="qwen-plus",
        tokenizer="qwen",
        context_window=128000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.15,
    ),
    "qwen-max": ModelTokenConfig(
        name="qwen-max",
        tokenizer="qwen",
        context_window=32000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.15,
    ),
    "deepseek-chat": ModelTokenConfig(
        name="deepseek-chat",
        tokenizer="tiktoken",
        encoding="cl100k_base",
        context_window=32000,
        calculation_method=CalculationMethod.TIKTOKEN,
    ),
    "deepseek-coder": ModelTokenConfig(
        name="deepseek-coder",
        tokenizer="tiktoken",
        encoding="cl100k_base",
        context_window=16384,
        calculation_method=CalculationMethod.TIKTOKEN,
    ),
    "claude-3-opus": ModelTokenConfig(
        name="claude-3-opus",
        tokenizer="claude",
        context_window=200000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
    "claude-3-sonnet": ModelTokenConfig(
        name="claude-3-sonnet",
        tokenizer="claude",
        context_window=200000,
        calculation_method=CalculationMethod.API_OR_ESTIMATE,
        conservative_ratio=1.2,
    ),
}


class TokenCalculator:
    """
    Token 精确计算器
    
    支持多种模型的 Token 计算：
    - OpenAI 系列: 使用 tiktoken 精确计算
    - 国产模型: 使用字符估算（保守策略）
    
    使用示例：
        calc = TokenCalculator(model_name="gpt-4")
        tokens = calc.count_tokens("你好，世界")
        
        # 计算消息的 Token
        message = {"role": "user", "content": "你好"}
        tokens = calc.count_message_tokens(message)
    
    Reference: docs/2026/04/01/DESIGN_CONTEXT_TOKEN_ECONOMICS.md
    """
    
    DEFAULT_MODEL = "gpt-4"
    DEFAULT_ENCODING = "cl100k_base"
    
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        """
        初始化 Token 计算器
        
        Args:
            model_name: 模型名称
        """
        self.model_name = model_name.lower()
        self.config = self._get_model_config(self.model_name)
        self.encoding: Union[Any, None] = None
        
        if self.config.calculation_method == CalculationMethod.TIKTOKEN:
            self._init_tiktoken()
    
    def _get_model_config(self, model_name: str) -> ModelTokenConfig:
        """获取模型配置"""
        normalized = model_name.lower()
        
        for key, config in MODEL_CONFIGS.items():
            if key in normalized or normalized in key:
                return config
        
        if any(x in normalized for x in ["gpt", "deepseek"]):
            return MODEL_CONFIGS["gpt-4"]
        elif any(x in normalized for x in ["glm", "qwen", "claude"]):
            return ModelTokenConfig(
                name=model_name,
                tokenizer="unknown",
                context_window=128000,
                calculation_method=CalculationMethod.API_OR_ESTIMATE,
                conservative_ratio=1.3,
            )
        
        return MODEL_CONFIGS[self.DEFAULT_MODEL]
    
    def _init_tiktoken(self) -> None:
        """初始化 tiktoken 编码器"""
        try:
            import tiktoken
            
            encoding_name = self.config.encoding or self.DEFAULT_ENCODING
            try:
                self.encoding = tiktoken.encoding_for_model(self.model_name)
            except KeyError:
                self.encoding = tiktoken.get_encoding(encoding_name)
            
            logger.debug(f"Initialized tiktoken encoding for {self.model_name}")
        except ImportError:
            logger.warning("tiktoken not installed, falling back to estimation")
            self.config = ModelTokenConfig(
                name=self.model_name,
                tokenizer="fallback",
                context_window=self.config.context_window,
                calculation_method=CalculationMethod.ESTIMATE,
                conservative_ratio=1.3,
            )
    
    def count_tokens(self, text: str) -> int:
        """
        计算 Token 数量
        
        Args:
            text: 要计算的文本
            
        Returns:
            Token 数量
        """
        if not text:
            return 0
        
        if self.config.calculation_method == CalculationMethod.TIKTOKEN:
            return self._count_with_tiktoken(text)
        else:
            return self._count_with_estimate(text)
    
    def _count_with_tiktoken(self, text: str) -> int:
        """使用 tiktoken 精确计算"""
        if self.encoding is None:
            return self._count_with_estimate(text)
        
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken encoding failed: {e}, falling back to estimate")
            return self._count_with_estimate(text)
    
    def _count_with_estimate(self, text: str) -> int:
        """
        使用字符估算计算 Token
        
        保守策略：
        - 中文为主: 1 token ≈ 1.5-2 字符
        - 英文为主: 1 token ≈ 3-4 字符
        - 混合内容: 1 token ≈ 2.5 字符
        
        使用 conservative_ratio 进行保守调整
        """
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        if total_chars == 0:
            return 0
        
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.5:
            estimated = int(total_chars / 1.8)
        elif chinese_ratio < 0.2:
            estimated = int(total_chars / 3.5)
        else:
            estimated = int(total_chars / 2.5)
        
        result = int(estimated * self.config.conservative_ratio)
        return max(1, result)
    
    def count_message_tokens(self, message: Dict[str, Any]) -> int:
        """
        计算消息的 Token 数量（包含格式开销）
        
        OpenAI 消息格式开销：
        - 每个 <|im_start|> + role: ~4 tokens
        - 每个 <|im_end|>: ~1 token
        
        Args:
            message: 消息字典，包含 role 和 content
            
        Returns:
            Token 数量
        """
        overhead = 4
        
        content = message.get("content", "")
        if isinstance(content, str):
            content_tokens = self.count_tokens(content)
        else:
            content_tokens = sum(
                self.count_tokens(block.get("text", ""))
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        
        role = message.get("role", "")
        role_tokens = self.count_tokens(role) if role else 0
        
        return overhead + role_tokens + content_tokens
    
    def count_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        计算消息列表的总 Token 数量
        
        Args:
            messages: 消息列表
            
        Returns:
            总 Token 数量
        """
        return sum(self.count_message_tokens(msg) for msg in messages)
    
    def get_context_window(self) -> int:
        """获取模型的上下文窗口大小"""
        return self.config.context_window
    
    def get_calculation_method(self) -> str:
        """获取当前使用的计算方式"""
        return self.config.calculation_method.value
    
    def is_precise(self) -> bool:
        """是否使用精确计算"""
        return self.config.calculation_method == CalculationMethod.TIKTOKEN