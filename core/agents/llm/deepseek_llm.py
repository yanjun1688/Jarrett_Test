"""
DeepSeek LLM 服务实现
使用 OpenAI 兼容 API 格式
"""
from .base_llm import OpenAICompatibleService
import logging

logger = logging.getLogger(__name__)


class DeepSeekLLMService(OpenAICompatibleService):
    """
    DeepSeek LLM 服务实现
    使用 OpenAI 兼容 API: https://api.deepseek.com
    """

    def __init__(self, config=None, provider=None):
        """DeepSeek OpenAI 兼容端点"""
        self.base_url = "https://api.deepseek.com"
        super().__init__(config, provider)
        logger.info(f"DeepSeek (OpenAI 兼容模式) initialized with model: {self.config.model_name}")
