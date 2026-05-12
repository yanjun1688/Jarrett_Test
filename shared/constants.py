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


# 文档类型
class DocType:
    """知识库文档类型常量 — 仅限知识型文档"""
    PRD = 'prd'
    API_DOC = 'api_doc'
    BEST_PRACTICE = 'best_practice'
    CODE_EXAMPLE = 'code_example'
    TEST_PATTERN = 'test_pattern'
    
    ALL = [PRD, API_DOC, BEST_PRACTICE, CODE_EXAMPLE, TEST_PATTERN]
    
    @classmethod
    def is_valid(cls, doc_type: str) -> bool:
        return doc_type in cls.ALL


