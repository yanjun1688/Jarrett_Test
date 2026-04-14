"""
Qwen LLM 服务实现
使用阿里云 DashScope OpenAI 兼容 API 格式
"""
from .base_llm import OpenAICompatibleService
import logging

logger = logging.getLogger(__name__)


class QwenLLMService(OpenAICompatibleService):
    """
    Qwen LLM 服务实现
    使用阿里云 DashScope OpenAI 兼容 API: https://dashscope.aliyuncs.com/compatible-mode/v1
    """

    def __init__(self, config=None, provider=None):
        """DashScope OpenAI 兼容端点"""
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        super().__init__(config, provider)
        logger.info(f"Qwen (DashScope 兼容模式) initialized with model: {self.config.model_name}")
