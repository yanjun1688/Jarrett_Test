"""
常量定义
"""

# 测试类型
class TestType:
    """测试类型常量"""
    UI = "ui"
    API = "api"
    INTEGRATION = "integration"
    AUTO = "auto"
    
    ALL = [UI, API, INTEGRATION, AUTO]
    
    @classmethod
    def is_valid(cls, test_type: str) -> bool:
        """验证测试类型是否有效"""
        return test_type in cls.ALL


# 节点类型
class NodeType:
    """节点类型常量"""
    # UI测试节点
    UI_NAVIGATE = "ui_navigate"
    UI_CLICK = "ui_click"
    UI_INPUT = "ui_input"
    UI_ASSERT = "ui_assert"
    UI_WAIT = "ui_wait"
    
    # API测试节点
    API_REQUEST = "api_request"
    API_VALIDATE = "api_validate"
    API_EXTRACT = "api_extract"
    
    # 控制节点
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    
    # 工具节点
    DATA_GENERATOR = "data_generator"
    TRANSFORM = "transform"
    LOG = "log"
    
    # UI节点列表
    UI_NODES = [UI_NAVIGATE, UI_CLICK, UI_INPUT, UI_ASSERT, UI_WAIT]
    
    # API节点列表
    API_NODES = [API_REQUEST, API_VALIDATE, API_EXTRACT]
    
    # 控制节点列表
    CONTROL_NODES = [CONDITION, LOOP, PARALLEL]
    
    # 工具节点列表
    TOOL_NODES = [DATA_GENERATOR, TRANSFORM, LOG]
    
    @classmethod
    def get_category(cls, node_type: str) -> str:
        """获取节点类型所属的类别"""
        if node_type in cls.UI_NODES:
            return "ui"
        elif node_type in cls.API_NODES:
            return "api"
        elif node_type in cls.CONTROL_NODES:
            return "control"
        elif node_type in cls.TOOL_NODES:
            return "tool"
        else:
            return "unknown"


# HTTP方法
class HttpMethod:
    """HTTP方法常量"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    
    ALL = [GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS]
    
    @classmethod
    def is_valid(cls, method: str) -> bool:
        """验证HTTP方法是否有效"""
        return method.upper() in cls.ALL


# 执行状态
class ExecutionStatus:
    """执行状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    
    ALL = [PENDING, RUNNING, SUCCESS, FAILED, CANCELLED, TIMEOUT, SKIPPED]
    
    # 完成状态
    COMPLETED = [SUCCESS, FAILED, CANCELLED, TIMEOUT, SKIPPED]
    
    # 活动状态
    ACTIVE = [PENDING, RUNNING]
    
    @classmethod
    def is_completed(cls, status: str) -> bool:
        """检查状态是否已完成"""
        return status in cls.COMPLETED
    
    @classmethod
    def is_active(cls, status: str) -> bool:
        """检查状态是否活动"""
        return status in cls.ACTIVE


# 断言类型
class AssertionType:
    """断言类型常量"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    MATCHES_REGEX = "matches_regex"
    
    ALL = [
        EQUALS, NOT_EQUALS, CONTAINS, NOT_CONTAINS,
        GREATER_THAN, LESS_THAN, GREATER_THAN_OR_EQUAL, LESS_THAN_OR_EQUAL,
        IS_NULL, IS_NOT_NULL, IS_TRUE, IS_FALSE, MATCHES_REGEX
    ]
    
    @classmethod
    def is_valid(cls, assertion_type: str) -> bool:
        """验证断言类型是否有效"""
        return assertion_type in cls.ALL


# 日志级别
class LogLevel:
    """日志级别常量"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    ALL = [DEBUG, INFO, WARNING, ERROR, CRITICAL]
    
    @classmethod
    def get_numeric_level(cls, level: str) -> int:
        """获取日志级别的数值"""
        levels = {
            cls.DEBUG: 10,
            cls.INFO: 20,
            cls.WARNING: 30,
            cls.ERROR: 40,
            cls.CRITICAL: 50
        }
        return levels.get(level.upper(), 20)  # 默认INFO


# 错误代码
class ErrorCode:
    """错误代码常量"""
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    
    # 认证授权错误
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    
    # 业务错误
    PLANNING_ERROR = "PLANNING_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # 外部服务错误
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    LLM_ERROR = "LLM_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # 限流错误
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"


# 时间常量（秒）
class TimeConstants:
    """时间常量"""
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    
    # 默认超时时间
    DEFAULT_TIMEOUT = 30
    DEFAULT_EXECUTION_TIMEOUT = 300
    DEFAULT_HTTP_TIMEOUT = 10
    
    # 重试相关
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_MAX_RETRIES = 3


# 文件大小常量（字节）
class FileSize:
    """文件大小常量"""
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB
    TB = 1024 * GB
    
    # 限制
    MAX_UPLOAD_SIZE = 10 * MB
    MAX_DOCUMENT_SIZE = 5 * MB
    MAX_IMAGE_SIZE = 2 * MB


# 数据库常量
class DatabaseConstants:
    """数据库常量"""
    # 默认值
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    DEFAULT_TOP_K = 5
    
    # 限制
    MAX_QUERY_RESULTS = 1000
    MAX_BATCH_SIZE = 100
    MAX_TRANSACTION_RETRIES = 3


# API常量
class ApiConstants:
    """API常量"""
    # 版本
    CURRENT_VERSION = "v1"
    
    # 分页
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # 排序
    DEFAULT_SORT_FIELD = "created_at"
    DEFAULT_SORT_ORDER = "desc"
    
    # 响应格式
    SUCCESS_RESPONSE = {"success": True}
    ERROR_RESPONSE = {"success": False}


# 正则表达式模式
class RegexPattern:
    """正则表达式模式常量"""
    # 邮箱
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # URL
    URL = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    
    # 手机号（中国）
    PHONE_CN = r'^1[3-9]\d{9}$'
    
    # 身份证号（中国）
    ID_CARD_CN = r'^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$'
    
    # IP地址
    IP_ADDRESS = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    # 日期（YYYY-MM-DD）
    DATE_YYYY_MM_DD = r'^\d{4}-\d{2}-\d{2}$'
    
    # 时间（HH:MM:SS）
    TIME_HH_MM_SS = r'^\d{2}:\d{2}:\d{2}$'
    
    # 日期时间（YYYY-MM-DD HH:MM:SS）
    DATETIME = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'


# 意图类型
class IntentType:
    """Chatbot意图类型常量
    
    基于集合论 + 谓词逻辑的三维模型 (V, O, M)
    
    意图分类：
    - 生成类：GENERATE_TESTCASE, GENERATE_UI_TEST, GENERATE_API_TEST, GENERATE_PRD
    - 查询类：QUERY_TESTCASE, QUERY_KNOWLEDGE, QUERY_PRD
    - 执行类：EXECUTE_TEST, RUN_TOOL
    - 其他：CHAT, HELP, SHOW_CASES
    
    Reference: core/agents/intent/ 模块文档
    """
    
    CHAT = "chat"
    
    # ── 生成类意图 ──────────────────────────────────────────────────
    GENERATE_TESTCASE = "generate_testcase"
    GENERATE_UI_TEST = "generate_ui_test"
    GENERATE_API_TEST = "generate_api_test"
    GENERATE_PRD = "generate_prd"
    
    # ── 查询类意图 ──────────────────────────────────────────────────
    QUERY_KNOWLEDGE = "query_knowledge"
    QUERY_TESTCASE = "query_testcase"
    QUERY_PRD = "query_prd"
    
    # ── 执行类意图 ──────────────────────────────────────────────────
    EXECUTE_TEST = "execute_test"
    RUN_TOOL = "run_tool"
    
    # ── 其他意图 ─────────────────────────────────────────────────────
    SHOW_CASES = "show_cases"
    HELP = "help"
    
    # ── 分类辅助方法 ────────────────────────────────────────────────
    
    @classmethod
    def is_generate_type(cls, intent: str) -> bool:
        """是否为生成类意图"""
        return intent in [
            cls.GENERATE_TESTCASE,
            cls.GENERATE_UI_TEST,
            cls.GENERATE_API_TEST,
            cls.GENERATE_PRD
        ]
    
    @classmethod
    def is_query_type(cls, intent: str) -> bool:
        """是否为查询类意图"""
        return intent in [
            cls.QUERY_KNOWLEDGE,
            cls.QUERY_TESTCASE,
            cls.QUERY_PRD
        ]
    
    @classmethod
    def all_intents(cls) -> list[str]:
        """返回所有意图类型"""
        return [
            cls.CHAT,
            cls.GENERATE_TESTCASE,
            cls.GENERATE_UI_TEST,
            cls.GENERATE_API_TEST,
            cls.GENERATE_PRD,
            cls.QUERY_KNOWLEDGE,
            cls.QUERY_TESTCASE,
            cls.QUERY_PRD,
            cls.EXECUTE_TEST,
            cls.RUN_TOOL,
            cls.SHOW_CASES,
            cls.HELP
        ]


# 文档类型
class DocType:
    """知识库文档类型常量"""
    PRD = "prd"
    API_DOC = "api_doc"
    FEATURE_TEST = "feature_test"
    API_TEST = "api_test"
    UI_TEST = "ui_test"
    
    ALL = [PRD, API_DOC, FEATURE_TEST, API_TEST, UI_TEST]
    TEST_TYPES = [FEATURE_TEST, API_TEST, UI_TEST]
    DOC_TYPES = [PRD, API_DOC]
    
    @classmethod
    def is_valid(cls, doc_type: str) -> bool:
        return doc_type in cls.ALL
    
    @classmethod
    def is_test_type(cls, doc_type: str) -> bool:
        return doc_type in cls.TEST_TYPES
    
    @classmethod
    def is_doc_type(cls, doc_type: str) -> bool:
        return doc_type in cls.DOC_TYPES


# 环境变量名称
class EnvVar:
    """环境变量名称常量"""
    # 数据库
    DATABASE_URL = "DATABASE_URL"
    
    # LLM
    LLM_API_KEY = "LLM_API_KEY"
    LLM_BASE_URL = "LLM_BASE_URL"
    LLM_MODEL = "LLM_MODEL"
    
    # 向量存储
    VECTOR_STORE_URL = "VECTOR_STORE_URL"
    VECTOR_STORE_API_KEY = "VECTOR_STORE_API_KEY"
    
    # 应用配置
    DEBUG = "DEBUG"
    SECRET_KEY = "SECRET_KEY"
    ALLOWED_HOSTS = "ALLOWED_HOSTS"
    
    # 日志
    LOG_LEVEL = "LOG_LEVEL"
    LOG_FILE = "LOG_FILE"