"""
脚本执行策略单元测试
测试策略模式、工厂模式和各种脚本类型的执行策略
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from django.core.files import File

from testmanager_app.execution_strategies import (
    ScriptExecutionStatus,
    StrategyNotFoundError,
    ExecutionStrategyInterface,
    ApiYamlScriptStrategy,  # 修复：重命名
    DefaultScriptStrategy,
    ScriptExecutionStrategyFactory
)
from testmanager_app.models import TestScript, ScriptExecution


class TestScriptExecutionStatus:
    """测试脚本执行状态枚举"""

    def test_status_values(self):
        """测试状态枚举值"""
        assert ScriptExecutionStatus.SUCCESS.value == "success"
        assert ScriptExecutionStatus.FAILED.value == "failed"
        assert ScriptExecutionStatus.ERROR.value == "error"


class TestExecutionStrategyInterface:
    """测试执行策略接口"""

    def test_interface_is_abstract(self):
        """测试接口是抽象类"""
        with pytest.raises(TypeError):
            ExecutionStrategyInterface()

    def test_concrete_strategy_must_implement_methods(self):
        """测试具体策略必须实现所有抽象方法"""
        class IncompleteStrategy(ExecutionStrategyInterface):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()


class TestApiYamlScriptStrategy:
    """测试API/YAML脚本执行策略"""

    @pytest.fixture
    def strategy(self):
        return ApiYamlScriptStrategy()

    @pytest.fixture
    def api_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'api'
        script.id = 1
        script.name = 'test_api_script'
        # 修复：使用 content 字段而不是 file.read()
        script.content = '{"test": "content"}'
        return script

    @pytest.fixture
    def yaml_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'yaml'
        script.id = 3
        script.name = 'test_yaml_script'
        # 修复：使用 content 字段而不是 file.read()
        script.content = 'test: yaml content'
        return script

    @pytest.fixture
    def execution(self):
        execution = Mock(spec=ScriptExecution)
        execution.output = None
        execution.error_message = None
        execution.status = None
        return execution

    def test_can_execute_supported_types(self, strategy, api_script, yaml_script):
        """测试可以执行支持的脚本类型"""
        assert strategy.can_execute(api_script) is True
        assert strategy.can_execute(yaml_script) is True

    def test_cannot_execute_unsupported_type(self, strategy):
        """测试不能执行不支持的脚本类型"""
        unsupported_script = Mock(spec=TestScript)
        unsupported_script.script_type = 'python'
        assert strategy.can_execute(unsupported_script) is False

    @patch('testmanager_app.execution_strategies.TestChainExecutor')
    def test_execute_successful_api_script(self, mock_executor_class, strategy, api_script, execution):
        """测试成功执行API脚本"""
        # 模拟成功的执行结果
        mock_executor = Mock()
        mock_executor.execute_test_chain.return_value = {
            'success': True,
            'logs': ['Test started', 'Test completed successfully']
        }
        mock_executor_class.return_value = mock_executor

        result = strategy.execute(api_script, execution)

        # 验证执行器被正确调用（修复：使用 script_type 而不是 file.name）
        mock_executor.execute_test_chain.assert_called_once_with(
            '{"test": "content"}',
            'api'  # 使用 script.script_type 而不是基于文件名检测
        )

        # 验证执行结果
        assert result.status == ScriptExecutionStatus.SUCCESS.value
        assert result.output == "Test started\nTest completed successfully"
        assert result.error_message is None

    @patch('testmanager_app.execution_strategies.TestChainExecutor')
    def test_execute_failed_api_script(self, mock_executor_class, strategy, api_script, execution):
        """测试执行失败的API脚本"""
        # 模拟失败的执行结果
        mock_executor = Mock()
        mock_executor.execute_test_chain.return_value = {
            'success': False,
            'logs': ['Test started', 'Test failed'],
            'error': 'Assertion failed'
        }
        mock_executor_class.return_value = mock_executor

        result = strategy.execute(api_script, execution)

        assert result.status == ScriptExecutionStatus.FAILED.value
        assert result.output == "Test started\nTest failed"
        assert result.error_message == "Assertion failed"

    @patch('testmanager_app.execution_strategies.TestChainExecutor')
    def test_execute_with_execution_exception(self, mock_executor_class, strategy, api_script, execution):
        """测试执行过程中出现异常"""
        # 模拟执行器抛出异常
        mock_executor = Mock()
        mock_executor.execute_test_chain.side_effect = Exception("Test execution error")
        mock_executor_class.return_value = mock_executor

        result = strategy.execute(api_script, execution)

        assert result.status == ScriptExecutionStatus.ERROR.value
        assert "Test execution error" in result.error_message
        assert "Test execution error" in result.output


    def test_execute_with_non_string_logs(self, strategy, api_script, execution):
        """测试处理非字符串类型的日志"""
        with patch('testmanager_app.execution_strategies.TestChainExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_test_chain.return_value = {
                'success': True,
                'logs': [123, None, 'string log', {'key': 'value'}]
            }
            mock_executor_class.return_value = mock_executor

            result = strategy.execute(api_script, execution)

            assert result.status == ScriptExecutionStatus.SUCCESS.value
            assert "123" in result.output
            assert "None" in result.output
            assert "string log" in result.output
            assert str({'key': 'value'}) in result.output

    def test_execute_with_missing_logs(self, strategy, api_script, execution):
        """测试处理缺失日志的情况"""
        with patch('testmanager_app.execution_strategies.TestChainExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_test_chain.return_value = {
                'success': True
                # 没有logs字段
            }
            mock_executor_class.return_value = mock_executor

            result = strategy.execute(api_script, execution)

            assert result.output == ""  # 空字符串


class TestDefaultScriptStrategy:
    """测试默认脚本执行策略"""

    @pytest.fixture
    def strategy(self):
        return DefaultScriptStrategy()

    @pytest.fixture
    def unknown_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'unknown_type'
        script.id = 1
        script.name = 'test_unknown_script'
        return script

    @pytest.fixture
    def execution(self):
        execution = Mock(spec=ScriptExecution)
        execution.output = None
        execution.error_message = None
        execution.status = None
        return execution

    def test_can_execute_any_script(self, strategy):
        """测试可以执行任何脚本类型"""
        any_script = Mock(spec=TestScript)
        any_script.script_type = 'any_type'
        assert strategy.can_execute(any_script) is True

    def test_execute_unknown_script_returns_error(self, strategy, unknown_script, execution):
        """测试执行未知脚本类型返回错误"""
        result = strategy.execute(unknown_script, execution)

        assert result.status == ScriptExecutionStatus.ERROR.value
        assert "Unknown script type" in result.output
        assert "unknown_type" in result.output
        assert result.error_message == "Unsupported script type: unknown_type"

    def test_execute_preserves_execution_object(self, strategy, unknown_script, execution):
        """测试执行方法保持执行对象的一致性"""
        result = strategy.execute(unknown_script, execution)
        assert result is execution


class TestScriptExecutionStrategyFactory:
    """测试脚本执行策略工厂"""

    @pytest.fixture
    def factory(self):
        # 清除工厂状态，确保测试独立
        ScriptExecutionStrategyFactory._strategies = None
        return ScriptExecutionStrategyFactory

    @pytest.fixture
    def python_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'python'
        script.id = 1
        return script

    @pytest.fixture
    def api_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'api'
        script.id = 2
        return script

    @pytest.fixture
    def unknown_script(self):
        script = Mock(spec=TestScript)
        script.script_type = 'unknown'
        script.id = 3
        return script

    def test_factory_initialization(self, factory):
        """测试工厂初始化"""
        assert factory._strategies is None
        factory._initialize_strategies()
        assert factory._strategies is not None
        assert len(factory._strategies) == 2  # 现在只有 ApiYamlScriptStrategy 和 DefaultScriptStrategy

    def test_get_strategy_for_api_script(self, factory, api_script):
        """测试获取API脚本的执行策略"""
        strategy = factory.get_strategy(api_script)
        assert isinstance(strategy, ApiYamlScriptStrategy)

    def test_get_strategy_for_unknown_script(self, factory, unknown_script):
        """测试获取未知脚本类型的执行策略"""
        strategy = factory.get_strategy(unknown_script)
        assert isinstance(strategy, DefaultScriptStrategy)

    def test_strategy_ordering(self, factory):
        """测试策略优先级排序"""
        # DefaultStrategy应该最后检查
        factory._initialize_strategies()
        strategies = factory._strategies

        # 最后一个应该是DefaultScriptStrategy
        assert isinstance(strategies[-1], DefaultScriptStrategy)

        # ApiYamlScriptStrategy应该在DefaultScriptStrategy之前
        api_yaml_index = next(i for i, s in enumerate(strategies) if isinstance(s, ApiYamlScriptStrategy))
        default_index = next(i for i, s in enumerate(strategies) if isinstance(s, DefaultScriptStrategy))
        assert api_yaml_index < default_index

    def test_register_new_strategy(self, factory):
        """测试注册新策略"""
        class CustomStrategy(ExecutionStrategyInterface):
            def can_execute(self, script):
                return script.script_type == 'custom'

            def execute(self, script, execution):
                execution.status = ScriptExecutionStatus.SUCCESS.value
                return execution

        custom_strategy = CustomStrategy()
        factory.register_strategy(custom_strategy)

        # 验证策略已注册
        custom_script = Mock(spec=TestScript)
        custom_script.script_type = 'custom'

        strategy = factory.get_strategy(custom_script)
        assert strategy is custom_strategy

        # 验证策略列表已更新
        strategies = factory.get_registered_strategies()
        assert custom_strategy in strategies

    def test_get_registered_strategies(self, factory):
        """测试获取所有已注册的策略"""
        strategies = factory.get_registered_strategies()
        assert len(strategies) == 2  # 现在只有 ApiYamlScriptStrategy 和 DefaultScriptStrategy
        assert any(isinstance(s, ApiYamlScriptStrategy) for s in strategies)
        assert any(isinstance(s, DefaultScriptStrategy) for s in strategies)

    def test_get_registered_strategies_returns_copy(self, factory):
        """测试获取已注册策略返回的是副本"""
        strategies1 = factory.get_registered_strategies()
        strategies2 = factory.get_registered_strategies()

        assert strategies1 is not strategies2
        assert strategies1 == strategies2

    def test_multiple_initializations(self, factory):
        """测试多次初始化不会重复创建策略"""
        factory._initialize_strategies()
        first_strategies = factory._strategies.copy()

        factory._initialize_strategies()
        second_strategies = factory._strategies.copy()

        # 应该是同一个列表对象
        assert first_strategies is second_strategies

    def test_strategy_not_found_error_scenario(self, factory):
        """测试理论上不会发生的策略未找到错误场景"""
        # 模拟一个极端情况：没有任何策略可以处理脚本
        factory._strategies = []  # 清空策略列表

        any_script = Mock(spec=TestScript)
        any_script.script_type = 'any'

        with pytest.raises(StrategyNotFoundError) as exc_info:
            factory.get_strategy(any_script)

        assert "No strategy found" in str(exc_info.value)
        assert "any" in str(exc_info.value)


class TestStrategyIntegration:
    """测试策略集成场景"""

    @pytest.fixture
    def factory(self):
        ScriptExecutionStrategyFactory._strategies = None
        return ScriptExecutionStrategyFactory

    @patch('testmanager_app.execution_strategies.TestChainExecutor')
    def test_end_to_end_api_script_execution(self, mock_executor_class, factory):
        """测试API脚本的端到端执行"""
        script = Mock(spec=TestScript)
        script.script_type = 'api'
        script.id = 1
        script.name = 'api_test'
        # 修复：使用 content 字段而不是 file
        script.content = '{"test": "api content"}'

        execution = Mock(spec=ScriptExecution)
        execution.output = None
        execution.error_message = None
        execution.status = None

        # 模拟执行器
        mock_executor = Mock()
        mock_executor.execute_test_chain.return_value = {
            'success': True,
            'logs': ['API test started', 'All assertions passed']
        }
        mock_executor_class.return_value = mock_executor

        # 获取策略并执行
        strategy = factory.get_strategy(script)
        result = strategy.execute(script, execution)

        # 验证执行结果
        assert isinstance(strategy, ApiYamlScriptStrategy)
        assert result.status == ScriptExecutionStatus.SUCCESS.value
        assert "API test started" in result.output
        assert "All assertions passed" in result.output
        assert result.error_message is None

    def test_end_to_end_unknown_script_execution(self, factory):
        """测试未知脚本类型的端到端执行"""
        script = Mock(spec=TestScript)
        script.script_type = 'unknown_format'
        script.id = 1
        script.name = 'unknown_script'

        execution = Mock(spec=ScriptExecution)
        execution.output = None
        execution.error_message = None
        execution.status = None

        # 获取策略并执行
        strategy = factory.get_strategy(script)
        result = strategy.execute(script, execution)

        # 验证执行结果（应该使用默认策略）
        assert isinstance(strategy, DefaultScriptStrategy)
        assert result.status == ScriptExecutionStatus.ERROR.value
        assert "Unknown script type" in result.output
        assert "unknown_format" in result.output


if __name__ == '__main__':
    pytest.main([__file__])