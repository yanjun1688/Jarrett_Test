"""
统一配置管理
使用pydantic进行类型安全的配置管理
"""
import os
from typing import Optional, Any
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class JTestSettings(BaseSettings):
    """JTest项目统一配置"""
    
    # LLM配置
    llm_provider: str = Field(default="qwen", description="LLM提供商")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API密钥")
    llm_base_url: Optional[str] = Field(default=None, description="LLM基础URL")
    llm_model: str = Field(default="qwen3-coder-plus", description="LLM模型名称")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM温度")
    llm_max_tokens: int = Field(default=4000, ge=1, description="LLM最大token数")
    
    # RAG配置
    rag_enabled: bool = Field(default=True, description="是否启用RAG")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding模型"
    )
    chunk_size: int = Field(default=1000, ge=100, description="分块大小")
    chunk_overlap: int = Field(default=200, ge=0, description="分块重叠")
    top_k: int = Field(default=5, ge=1, description="检索top K结果")
    embedding_batch_size: int = Field(default=32, ge=1, description="Embedding批处理大小")
    
    # ChromaDB配置
    chromadb_path: str = Field(
        default="./data/chromadb",
        description="ChromaDB持久化存储路径"
    )
    chromadb_collection_name: str = Field(
        default="kb_knowledge",
        description="ChromaDB全局知识库集合名称"
    )

    # 对话记忆 RAG 配置
    memory_retrieval_top_k: int = Field(default=5, ge=1, le=20, description="对话记忆检索返回条数")
    memory_index_min_length: int = Field(default=10, ge=0, description="消息最小索引长度（字符）")
    
    # BM25配置
    bm25_index_path: str = Field(
        default="./data/bm25_index",
        description="BM25全文索引存储路径"
    )
    bm25_enabled: bool = Field(default=True, description="是否启用BM25混合搜索")
    bm25_top_k: int = Field(default=50, ge=1, description="BM25检索结果数")
    rrf_k: int = Field(default=60, ge=1, description="RRF融合常数k")
    
    # 执行配置
    max_concurrent_executions: int = Field(default=10, ge=1, description="最大并发执行数")
    execution_timeout: int = Field(default=600, ge=1, description="执行超时时间(秒)")
    retry_attempts: int = Field(default=3, ge=0, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试延迟(秒)")
    
    # 数据库配置
    database_url: str = Field(default="sqlite:///db.sqlite3", description="数据库URL")
    database_pool_size: int = Field(default=10, ge=1, description="数据库连接池大小")
    
    # 缓存配置
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=300, ge=0, description="缓存TTL(秒)")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # 测试配置
    test_timeout: int = Field(default=30, ge=1, description="测试超时时间(秒)")
    test_parallel: bool = Field(default=False, description="是否并行执行测试")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @model_validator(mode='before')
    @classmethod
    def load_llm_config_from_env(cls, values):
        """从环境变量读取 LLM 配置，自动推断 provider"""
        provider = values.get('llm_provider')

        # 未显式设置 provider 时自动检测
        if not provider:
            provider = cls._detect_provider()
        values['llm_provider'] = provider

        # 读取对应的 API Key
        key_map = {
            'zhipu': 'ZHIPU_API_KEY',
            'qwen': 'DASHSCOPE_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }
        env_key = key_map.get(provider)
        if env_key and not values.get('llm_api_key'):
            values['llm_api_key'] = os.getenv(env_key)

        # 读取对应的 Model Name
        model_map = {
            'zhipu': 'ZHIPU_MODEL_NAME',
            'qwen': 'QWEN_MODEL_NAME',
            'openai': 'OPENAI_MODEL_NAME',
        }
        env_model = model_map.get(provider)
        if env_model:
            model_val = os.getenv(env_model)
            if model_val:
                values['llm_model'] = model_val

        # 读取对应的 Base URL
        url_map = {
            'zhipu': 'ZHIPU_BASE_URL',
            'qwen': 'QWEN_BASE_URL',
            'openai': 'OPENAI_BASE_URL',
        }
        env_url = url_map.get(provider)
        if env_url and not values.get('llm_base_url'):
            url_val = os.getenv(env_url)
            if url_val:
                values['llm_base_url'] = url_val

        return values

    @classmethod
    def _detect_provider(cls) -> str:
        """从 .env 中已有的 API key 自动推断 LLM 提供商"""
        candidates = [
            ('ZHIPU_API_KEY', 'zhipu'),
            ('DASHSCOPE_API_KEY', 'qwen'),
            ('OPENAI_API_KEY', 'openai'),
            ('ANTHROPIC_API_KEY', 'anthropic'),
            ('DEEPSEEK_API_KEY', 'deepseek'),
        ]
        for env_var, provider in candidates:
            val = os.getenv(env_var, '')
            if val and 'your-' not in val and val != 'sk-your-key-here':
                return provider
        return 'qwen'  # fallback
    
    @model_validator(mode='after')
    def validate_llm_config(self):
        """验证 LLM 配置"""
        if not self.llm_api_key and self.llm_provider != 'mock':
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LLM API密钥为空，当前provider: {self.llm_provider}")
        return self
    
    @model_validator(mode='after')
    def validate_chunk_config(self):
        """验证分块配置"""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(f"chunk_overlap ({self.chunk_overlap}) 必须小于 chunk_size ({self.chunk_size})")
        return self


# 全局配置实例
settings = JTestSettings()


def get_settings() -> JTestSettings:
    """获取配置实例"""
    return settings


def update_settings(**kwargs: Any) -> JTestSettings:
    """更新配置"""
    global settings
    settings = JTestSettings(**{**settings.dict(), **kwargs})
    return settings