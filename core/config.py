"""
统一配置管理
使用pydantic进行类型安全的配置管理
"""
import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class JTestSettings(BaseSettings):
    """JTest项目统一配置"""
    
    # LLM配置
    llm_provider: str = Field(default="zhipu", description="LLM提供商")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API密钥")
    llm_base_url: Optional[str] = Field(default=None, description="LLM基础URL")
    llm_model: str = Field(default="glm-5", description="LLM模型名称")
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
    
    # ChromaDB配置
    chromadb_path: str = Field(
        default="./data/chromadb",
        description="ChromaDB持久化存储路径"
    )
    chromadb_collection_name: str = Field(
        default="kb_knowledge",
        description="ChromaDB全局知识库集合名称"
    )
    
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
        """从环境变量读取正确的 LLM 配置"""
        provider = values.get('llm_provider', 'zhipu')
        
        # 读取对应的 API Key
        if not values.get('llm_api_key'):
            if provider == 'zhipu':
                values['llm_api_key'] = os.getenv('ZHIPU_API_KEY')
            elif provider == 'qwen':
                values['llm_api_key'] = os.getenv('DASHSCOPE_API_KEY')
            elif provider == 'openai':
                values['llm_api_key'] = os.getenv('OPENAI_API_KEY')
            elif provider == 'anthropic':
                values['llm_api_key'] = os.getenv('ANTHROPIC_API_KEY')
            elif provider == 'deepseek':
                values['llm_api_key'] = os.getenv('DEEPSEEK_API_KEY')
        
        # 读取对应的 Model Name
        model_name = values.get('llm_model', '')
        if provider == 'zhipu':
            zhipu_model = os.getenv('ZHIPU_MODEL_NAME')
            if zhipu_model:
                values['llm_model'] = zhipu_model
        elif provider == 'qwen':
            qwen_model = os.getenv('QWEN_MODEL_NAME')
            if qwen_model:
                values['llm_model'] = qwen_model
        elif provider == 'openai':
            openai_model = os.getenv('OPENAI_MODEL_NAME')
            if openai_model:
                values['llm_model'] = openai_model
        
        return values
    
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


def update_settings(**kwargs) -> JTestSettings:
    """更新配置"""
    global settings
    settings = JTestSettings(**{**settings.dict(), **kwargs})
    return settings