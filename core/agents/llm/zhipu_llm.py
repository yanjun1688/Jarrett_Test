"""
智谱 AI (ZhipuAI) LLM 服务实现
使用 OpenAI 兼容 API 格式
支持 GLM-4.7-Flash 等模型
"""
import os
from typing import Optional, Dict, Any, List
from .base_llm import OpenAICompatibleService
import logging

logger = logging.getLogger(__name__)


class ZhipuLLMService(OpenAICompatibleService):
    """
    智谱 AI LLM 服务实现
    使用 OpenAI 兼容 API: https://open.bigmodel.cn/api/paas/v4/
    """

    def __init__(self, config: Optional[Any] = None, provider: Optional[Any] = None) -> None:
        """智谱 AI OpenAI 兼容端点"""
        self.base_url = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        if not self.base_url.endswith("/"):
            self.base_url += "/"
        super().__init__(config, provider)
        logger.info(f"智谱 AI (OpenAI 兼容模式) initialized with model: {self.config.model_name}, base_url: {self.base_url}")

    def _format_request_params(
        self,
        messages: List[Dict[str, str]],
        system_message: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        params = super()._format_request_params(
            messages=messages,
            system_message=system_message,
            tools=tools,
            **kwargs
        )

        if kwargs.get('response_format'):
            params['response_format'] = kwargs['response_format']

        thinking_enabled = kwargs.get('thinking_enabled', False)
        if thinking_enabled:
            params['thinking'] = {"type": "enabled"}

        return params
