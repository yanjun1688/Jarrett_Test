"""
Base Agent抽象类
所有Agent的基类，提供统一的接口和生命周期管理
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime

from shared.exceptions import JTestError
from shared.utils.logging_utils import get_logger, log_execution_time
from core.config import get_settings

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Agent基类
    
    所有Agent都应该继承此类，实现统一的接口和生命周期管理。
    """
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化Agent
        
        Args:
            agent_id: Agent唯一标识，如果为None则自动生成
            config: Agent配置
        """
        self.agent_id = agent_id or f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.config = config or {}
        self.settings = get_settings()
        
        # 状态管理
        self._state = {
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": None,
            "execution_count": 0,
            "error_count": 0
        }
        
        # 历史记录
        self._history: List[Dict[str, Any]] = []
        
        logger.info(f"初始化Agent: {self.agent_id} ({self.__class__.__name__})")
    
    @property
    def state(self) -> str:
        """Get current agent state"""
        return self._state.get("status", "unknown")
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化Agent
        
        子类应该实现此方法来加载资源、建立连接等。
        """
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Agent的主要功能
        
        Args:
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        清理资源
        
        子类应该实现此方法来释放资源、关闭连接等。
        """
        pass
    
    def update_state(self, status: str, **kwargs):
        """
        更新Agent状态
        
        Args:
            status: 新状态
            **kwargs: 其他状态字段
        """
        self._state["status"] = status
        self._state["last_activity"] = datetime.now().isoformat()
        self._state.update(kwargs)
        
        # 记录状态变更
        self._add_to_history("state_change", {
            "old_status": self._state.get("status"),
            "new_status": status,
            **kwargs
        })
    
    def _add_to_history(self, event_type: str, data: Dict[str, Any]):
        """
        添加历史记录
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "agent_id": self.agent_id,
            "data": data
        }
        self._history.append(history_entry)
        
        # 限制历史记录大小
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
    
    def get_state(self) -> Dict[str, Any]:
        """
        获取Agent状态
        
        Returns:
            Agent状态字典
        """
        return self._state.copy()
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            limit: 返回的记录数量限制
            
        Returns:
            历史记录列表
        """
        return self._history[-limit:] if limit > 0 else self._history.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.__class__.__name__,
            "execution_count": self._state.get("execution_count", 0),
            "error_count": self._state.get("error_count", 0),
            "success_rate": self._calculate_success_rate(),
            "average_execution_time": self._calculate_average_time(),
            "last_activity": self._state.get("last_activity"),
            "history_size": len(self._history)
        }
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        total = self._state.get("execution_count", 0)
        errors = self._state.get("error_count", 0)
        if total == 0:
            return 0.0
        return (total - errors) / total
    
    def _calculate_average_time(self) -> Optional[float]:
        """计算平均执行时间"""
        # 从历史记录中提取执行时间
        execution_times = []
        for entry in self._history:
            if entry["event_type"] == "execution" and "duration" in entry["data"]:
                execution_times.append(entry["data"]["duration"])
        
        if not execution_times:
            return None
        
        return sum(execution_times) / len(execution_times)
    
    def get_execution_time(self) -> float:
        """
        Get the last execution time in seconds
        
        Returns:
            Last execution time, or 0.0 if no execution recorded
        """
        for entry in reversed(self._history):
            if entry["event_type"] == "execution_complete" and "duration" in entry["data"]:
                return entry["data"]["duration"]
        return 0.0
    
    @log_execution_time()
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行Agent（包含错误处理和状态更新）
        
        Args:
            input_data: 输入数据
            
        Returns:
            执行结果
            
        Raises:
            JTestError: 执行失败
        """
        try:
            # 更新状态
            self.update_state("running")
            self._state["execution_count"] = self._state.get("execution_count", 0) + 1
            
            # 记录执行开始
            self._add_to_history("execution_start", {
                "input": input_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # 执行Agent
            start_time = datetime.now()
            result = await self.execute(input_data)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 记录执行完成
            self._add_to_history("execution_complete", {
                "result": result,
                "duration": duration,
                "timestamp": end_time.isoformat()
            })
            
            # 更新状态
            self.update_state("idle", last_execution_duration=duration)
            
            return {
                "success": True,
                "agent_id": self.agent_id,
                "result": result,
                "duration": duration,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            # 记录错误
            self._state["error_count"] = self._state.get("error_count", 0) + 1
            self._add_to_history("execution_error", {
                "error": str(e),
                "input": input_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # 更新状态
            self.update_state("error", last_error=str(e))
            
            logger.error(f"Agent执行失败: {self.agent_id}, 错误: {str(e)}", exc_info=True)
            
            # 转换为JTestError
            if isinstance(e, JTestError):
                raise e
            else:
                raise JTestError(f"Agent执行失败: {str(e)}", details={
                    "agent_id": self.agent_id,
                    "agent_type": self.__class__.__name__,
                    "input": input_data
                })
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    def validate_input(self, input_data: Dict[str, Any]) -> List[str]:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            错误消息列表，空列表表示验证通过
        """
        errors = []
        
        # 基本验证：输入必须是字典
        if not isinstance(input_data, dict):
            errors.append("输入数据必须是字典类型")  # type: ignore[unreachable]
            return errors
        
        # 子类可以重写此方法添加特定验证
        return errors
    
    def validate_output(self, output_data: Dict[str, Any]) -> List[str]:
        """
        验证输出数据
        
        Args:
            output_data: 输出数据
            
        Returns:
            错误消息列表，空列表表示验证通过
        """
        errors = []
        
        # 基本验证：输出必须是字典
        if not isinstance(output_data, dict):
            errors.append("输出数据必须是字典类型")  # type: ignore[unreachable]
            return errors
        
        # 子类可以重写此方法添加特定验证
        return errors
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取Agent能力描述
        
        Returns:
            能力描述字典
        """
        return {
            "agent_type": self.__class__.__name__,
            "description": getattr(self, "__doc__", "No description available"),
            "supports_async": True,
            "configurable": bool(self.config),
            "stateful": True
        }


class AgentFactory:
    """Agent工厂类"""
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, agent_type: str, agent_class: type):
        """注册Agent类"""
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent类必须继承自BaseAgent: {agent_class}")
        
        cls._registry[agent_type] = agent_class
        logger.info(f"注册Agent类型: {agent_type} -> {agent_class.__name__}")
    
    @classmethod
    def create(cls, agent_type: str, **kwargs) -> BaseAgent:
        """创建Agent实例"""
        if agent_type not in cls._registry:
            available_types = list(cls._registry.keys())
            raise ValueError(f"未知的Agent类型: {agent_type}. 可用类型: {available_types}")
        
        agent_class = cls._registry[agent_type]
        return agent_class(**kwargs)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """获取可用的Agent类型"""
        return list(cls._registry.keys())
    
    @classmethod
    def get_agent_info(cls, agent_type: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        if agent_type not in cls._registry:
            return None
        
        agent_class = cls._registry[agent_type]
        return {
            "type": agent_type,
            "class_name": agent_class.__name__,
            "module": agent_class.__module__,
            "description": getattr(agent_class, "__doc__", "No description"),
            "requires_config": hasattr(agent_class, "REQUIRED_CONFIG"),
            "default_config": getattr(agent_class, "DEFAULT_CONFIG", {})
        }