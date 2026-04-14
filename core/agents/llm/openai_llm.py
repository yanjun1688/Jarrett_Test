"""
OpenAI LLM 服务实现
使用 OpenAI 兼容 API 格式
"""
from .base_llm import OpenAICompatibleService
import logging

logger = logging.getLogger(__name__)


class OpenAILLMService(OpenAICompatibleService):
    """
    OpenAI LLM 服务实现
    使用标准 OpenAI API
    """

    def __init__(self, config=None, provider=None):
        """标准 OpenAI 端点"""
        super().__init__(config, provider)
        logger.info(f"OpenAI initialized with model: {self.config.model_name}")
