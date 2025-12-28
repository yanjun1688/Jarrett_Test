"""
脚本执行策略模块
提供不同脚本类型的执行策略实现，遵循策略模式和开闭原则
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum
from django.http import HttpResponse

from testmanager_app.models import TestScript, ScriptExecution

logger = logging.getLogger(__name__)


class ScriptExecutionStatus(Enum):
    """脚本执行状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class StrategyNotFoundError(Exception):
    """策略未找到异常"""
    pass


class ExecutionStrategyInterface(ABC):
    """
    脚本执行策略接口

    定义所有脚本执行策略必须实现的接口，遵循依赖倒置原则，
    高层模块（视图）依赖于抽象接口，而不是具体实现
    """

    @abstractmethod
    def execute(self, script: TestScript, execution: ScriptExecution) -> ScriptExecution:
        """
        执行脚本

        Args:
            script: 测试脚本对象
            execution: 脚本执行记录对象

        Returns:
            ScriptExecution: 更新后的执行记录对象
        """
        pass

    @abstractmethod
    def can_execute(self, script: TestScript) -> bool:
        """
        检查该策略是否可以执行给定的脚本

        Args:
            script: 测试脚本对象

        Returns:
            bool: 是否可以执行
        """
        pass


class ApiYamlScriptStrategy(ExecutionStrategyInterface):
    """API/YAML 脚本执行策略

    支持执行 API、YAML 格式的测试脚本
    使用 TestChainExecutor 执行测试链路
    """

    SUPPORTED_TYPES = ['api', 'yaml']

    def can_execute(self, script: TestScript) -> bool:
        """处理 api、yaml 类型的脚本"""
        return script.script_type in self.SUPPORTED_TYPES

    def execute(self, script: TestScript, execution: ScriptExecution) -> ScriptExecution:
        """执行 API/YAML 脚本"""
        try:
            # 修复：从 content 字段读取脚本内容（而不是 file 字段）
            script_content = script.content

            # 根据脚本类型判断格式
            script_format = script.script_type

            # 导入并执行测试链路
            from .script_engine import TestChainExecutor

            executor = TestChainExecutor()
            result = executor.execute_test_chain(script_content, script_format)

            # 保存执行结果
            execution.output = "\n".join(result['logs']) if isinstance(result.get('logs'), list) else str(result.get('logs', ''))
            execution.status = ScriptExecutionStatus.SUCCESS.value if result.get('success') else ScriptExecutionStatus.FAILED.value

            if not result.get('success'):
                execution.error_message = result.get('error', 'Unknown error occurred during script execution')

            logger.info(f"API/YAML脚本执行完成: script_id={script.id}, success={result.get('success')}")

        except Exception as e:
            logger.error(f"API/YAML脚本执行失败: script_id={script.id}, error={str(e)}", exc_info=True)
            execution.status = ScriptExecutionStatus.ERROR.value
            execution.error_message = f"Script execution failed: {str(e)}"
            execution.output = f"Error: {str(e)}"

        return execution


class DefaultScriptStrategy(ExecutionStrategyInterface):
    """默认脚本执行策略

    处理所有未知或不支持的脚本类型
    作为兜底策略，确保系统稳定性
    """

    def can_execute(self, script: TestScript) -> bool:
        """可以处理任何脚本（作为兜底）"""
        return True

    def execute(self, script: TestScript, execution: ScriptExecution) -> ScriptExecution:
        """处理未知脚本类型"""
        logger.warning(f"尝试执行未知的脚本类型: script_id={script.id}, type={script.script_type}")

        execution.output = f"Unknown script type: {script.script_type}"
        execution.error_message = f"Unsupported script type: {script.script_type}"
        execution.status = ScriptExecutionStatus.ERROR.value

        return execution


class ScriptExecutionStrategyFactory:
    """
    脚本执行策略工厂

    负责创建和管理脚本执行策略实例，实现策略的注册和获取
    遵循工厂模式和单例模式（策略实例复用）
    """

    _strategies = None  # 策略缓存，避免重复创建实例

    @classmethod
    def _initialize_strategies(cls):
        """初始化所有策略实例"""
        if cls._strategies is None:
            cls._strategies = [
                ApiYamlScriptStrategy(),  # 仅支持 API/YAML 脚本
                DefaultScriptStrategy(),  # 必须放在最后，作为兜底
            ]
            logger.info(f"初始化脚本执行策略工厂，注册 {len(cls._strategies)} 个策略")

    @classmethod
    def get_strategy(cls, script: TestScript) -> ExecutionStrategyInterface:
        """
        获取适合执行给定脚本的策略

        Args:
            script: 测试脚本对象

        Returns:
            ExecutionStrategyInterface: 策略实例

        Raises:
            StrategyNotFoundError: 如果找不到合适的策略
        """
        cls._initialize_strategies()

        # 按注册顺序查找第一个可以执行该脚本的策略
        for strategy in cls._strategies:
            if strategy.can_execute(script):
                logger.debug(f"找到策略: {strategy.__class__.__name__} 用于 script_id={script.id}")
                return strategy

        # 理论上不会到达这里，因为 DefaultScriptStrategy 可以处理所有情况
        logger.error(f"无法找到执行策略: script_id={script.id}, type={script.script_type}")
        raise StrategyNotFoundError(f"No strategy found for script type: {script.script_type}")

    @classmethod
    def register_strategy(cls, strategy: ExecutionStrategyInterface):
        """
        注册新的策略

        Args:
            strategy: 策略实例
        """
        cls._initialize_strategies()

        # 插入到列表前面（优先级高于默认策略）
        cls._strategies.insert(0, strategy)
        logger.info(f"注册新策略: {strategy.__class__.__name__}")

    @classmethod
    def get_registered_strategies(cls) -> list:
        """获取所有已注册的策略"""
        cls._initialize_strategies()
        return cls._strategies.copy()
