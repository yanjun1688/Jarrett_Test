"""
Execution Engine - orchestrates execution of test flows from Flow IR

重构版本：
- 使用 NodeFactory 进行 IR → Runtime 转换
- 清晰的控制流逻辑（基于 None 结束）
- 移除 ExecutableFlow 兼容代码
- BaseTestNode.execute() 直接返回 NodeExecutionResult
- 移除魔法字符串和 eval()
"""
from typing import Dict, Any, Optional, List, Callable, Set
import asyncio
import time
from datetime import datetime

from shared.exceptions import ExecutionError, ValidationError
from shared.utils.logging_utils import get_logger, log_execution_time
from shared.utils.async_utils import with_timeout, retry_async
from shared.constants import ExecutionStatus, TimeConstants

from .flow_ir import FlowIR, FlowNodeIR
from .node_factory import NodeFactory
from .test_node_registry import TestNodeRegistry
from .execution_metrics import NodeExecutionResult, FlowExecutionMetrics

logger = get_logger(__name__)


class ExecutionContext:
    """执行上下文"""
    
    def __init__(self, initial_context: Optional[Dict[str, Any]] = None):
        self._context = initial_context or {}
        self._variables = {}
        self._history = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self._context.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置上下文值"""
        self._context[key] = value
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "value": value
        })
    
    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新上下文"""
        self._context.update(updates)
        for key, value in updates.items():
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "key": key,
                "value": value
            })
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量值"""
        return self._variables.get(name, default)
    
    def set_variable(self, name: str, value: Any) -> None:
        """设置变量值"""
        self._variables[name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "context": self._context.copy(),
            "variables": self._variables.copy(),
            "history": self._history.copy()
        }
    
    def clone(self) -> 'ExecutionContext':
        """创建上下文的深拷贝"""
        cloned = ExecutionContext(self._context.copy())
        cloned._variables = self._variables.copy()
        cloned._history = self._history.copy()
        return cloned


class ExecutionEngine:
    """
    Execution Engine - orchestrates execution of test flows from Flow IR

    重构后的职责：
    - 使用 NodeFactory 进行节点实例化
    - 清晰的控制流逻辑（基于 on_success/on_failure）
    - 不再支持 ExecutableFlow（移除兼容代码）

    设计原则：
    - IR → Runtime 转换由 NodeFactory 负责
    - 控制流基于 on_success/on_failure，None 表示结束
    - BaseTestNode.execute() 直接返回 NodeExecutionResult
    - 移除魔法字符串（如 "end_success", "end_failure"）
    - 移除 eval() 安全风险
    """

    def __init__(
        self,
        registry: TestNodeRegistry,
        default_timeout: int = TimeConstants.DEFAULT_EXECUTION_TIMEOUT,
        max_retries: int = TimeConstants.DEFAULT_MAX_RETRIES
    ):
        """
        Initialize execution engine

        Args:
            registry: Test node registry for node type lookup
            default_timeout: Default timeout for flow execution in seconds
            max_retries: Maximum retry attempts for failed nodes
        """
        self.registry = registry
        self.node_factory = NodeFactory(registry)
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        # 事件回调
        self.on_node_start: Optional[Callable] = None
        self.on_node_complete: Optional[Callable] = None
        self.on_node_error: Optional[Callable] = None
        self.on_flow_complete: Optional[Callable] = None

    @log_execution_time()
    async def run(
        self,
        flow: FlowIR,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a test flow from Flow IR

        Args:
            flow: Flow IR to execute
            context: Initial execution context
            timeout: Execution timeout in seconds

        Returns:
            Dictionary containing execution results

        Raises:
            ValidationError: If flow is invalid
            ExecutionError: If execution fails
        """
        # 验证流程
        validation = flow.validate(strict=True)
        if validation["errors"]:
            raise ValidationError(
                "流程验证失败",
                details={"errors": validation["errors"], "warnings": validation["warnings"]}
            )
        
        if validation["warnings"]:
            logger.warning(f"流程验证警告: {validation['warnings']}")

        # 设置执行上下文
        exec_context = ExecutionContext(context or {})
        
        # 创建执行指标
        metrics = FlowExecutionMetrics()
        node_results: Dict[str, NodeExecutionResult] = {}
        errors: List[Dict[str, Any]] = []

        logger.info(f"开始执行流程: {flow.metadata.get('name', 'Untitled')}")
        logger.info(f"流程节点数: {len(flow.nodes)}")
        logger.info(f"起始节点: {flow.start_node}")

        start_time = time.time()

        try:
            # 使用超时包装执行
            execution_timeout = timeout or self.default_timeout
            
            @with_timeout(execution_timeout)
            async def execute_with_timeout():
                return await self._execute_flow(
                    flow, exec_context, metrics, node_results, errors
                )
            
            result = await execute_with_timeout()
            
            metrics.end_time = time.time()
            metrics.total_duration = metrics.end_time - start_time

            # 构建结果
            execution_result = {
                "success": metrics.failed_nodes == 0,
                "execution_id": str(int(time.time() * 1000)),
                "flow_name": flow.metadata.get("name", "Untitled"),
                "flow_metadata": flow.metadata,
                "node_results": {node_id: result.to_dict() for node_id, result in node_results.items()},
                "metrics": metrics.to_dict(),
                "context": exec_context.to_dict(),
                "errors": errors,
                "validation_warnings": validation["warnings"],
                "execution_time": metrics.total_duration
            }

            # 触发完成事件
            if self.on_flow_complete:
                self.on_flow_complete(execution_result)

            logger.info(f"流程执行完成: {flow.metadata.get('name', 'Untitled')}")
            logger.info(f"执行结果: {'成功' if metrics.failed_nodes == 0 else '失败'}")
            logger.info(f"执行统计: {metrics.to_dict()}")

            return execution_result

        except asyncio.TimeoutError:
            metrics.end_time = time.time()
            metrics.total_duration = metrics.end_time - start_time
            metrics.status = ExecutionStatus.TIMEOUT
            
            error_msg = f"流程执行超时: 超过 {execution_timeout} 秒"
            logger.error(error_msg)
            
            raise ExecutionError(error_msg, details={
                "timeout": execution_timeout,
                "executed_nodes": metrics.nodes_executed,
                "total_duration": metrics.total_duration
            })
        
        except Exception as e:
            metrics.end_time = time.time()
            metrics.total_duration = metrics.end_time - start_time
            metrics.status = ExecutionStatus.FAILED
            
            logger.error(f"流程执行失败: {str(e)}", exc_info=True)
            raise ExecutionError(f"流程执行失败: {str(e)}")

    async def _execute_flow(
        self,
        flow: FlowIR,
        context: ExecutionContext,
        metrics: FlowExecutionMetrics,
        node_results: Dict[str, NodeExecutionResult],
        errors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行流程内部方法"""
        current_node_id = flow.start_node
        visited_nodes: Set[str] = set()
        
        while current_node_id and current_node_id in flow.nodes:
            # 防止无限循环
            if current_node_id in visited_nodes:
                logger.warning(f"检测到循环执行，跳过节点: {current_node_id}")
                break
            
            visited_nodes.add(current_node_id)
            
            # 执行当前节点
            node_result = await self._execute_node(
                flow, current_node_id, context, metrics, errors
            )
            
            # 记录结果
            node_results[current_node_id] = node_result
            
            # 确定下一个节点
            if node_result.status == ExecutionStatus.SUCCESS:
                next_node_id = flow.nodes[current_node_id].on_success
            elif node_result.status == ExecutionStatus.FAILED:
                next_node_id = flow.nodes[current_node_id].on_failure
            else:
                # 其他状态（如跳过、取消等）也视为失败
                next_node_id = flow.nodes[current_node_id].on_failure
            
            current_node_id = next_node_id
        
        return {"completed": True}

    async def _execute_node(
        self,
        flow: FlowIR,
        node_id: str,
        context: ExecutionContext,
        metrics: FlowExecutionMetrics,
        errors: List[Dict[str, Any]]
    ) -> NodeExecutionResult:
        """执行单个节点"""
        node = flow.nodes[node_id]
        
        logger.info(f"执行节点: {node_id} ({node.node_type})")
        
        # 触发节点开始事件
        if self.on_node_start:
            self.on_node_start({
                "node_id": node_id,
                "node_type": node.node_type,
                "parameters": node.parameters,
                "metadata": node.metadata
            })
        
        start_time = time.time()
        node_result = NodeExecutionResult(node_id=node_id, node_type=node.node_type)
        
        try:
            # 检查条件
            if node.condition:
                condition_result = await self._evaluate_condition(node.condition, context)
                if not condition_result:
                    node_result.status = ExecutionStatus.SKIPPED
                    node_result.message = "条件不满足，跳过执行"
                    node_result.duration = time.time() - start_time
                    
                    logger.info(f"节点 {node_id} 条件不满足，跳过执行")
                    
                    # 触发节点完成事件
                    if self.on_node_complete:
                        self.on_node_complete(node_result.to_dict())
                    
                    metrics.skipped_nodes += 1
                    return node_result
            
            # 检查依赖关系
            if node.depends_on:
                missing_deps = []
                for dep_id in node.depends_on:
                    if dep_id not in metrics.completed_nodes:
                        missing_deps.append(dep_id)
                
                if missing_deps:
                    node_result.status = ExecutionStatus.FAILED
                    node_result.message = f"依赖节点未完成: {missing_deps}"
                    node_result.duration = time.time() - start_time
                    
                    logger.warning(f"节点 {node_id} 依赖未满足: {missing_deps}")
                    
                    # 触发节点错误事件
                    if self.on_node_error:
                        self.on_node_error(node_result.to_dict())
                    
                    metrics.failed_nodes += 1
                    return node_result
            
            # 执行节点
            async def execute_node():
                # 创建节点实例
                node_instance = self.node_factory.create_node(node)
                if not node_instance:
                    raise ExecutionError(f"无法创建节点实例: {node.node_type}")
                
                # 执行节点
                return await node_instance.execute(node.parameters, context.to_dict())
            
            # 重试机制
            execution_result = await retry_async(
                execute_node,
                max_attempts=self.max_retries,
                delay=TimeConstants.DEFAULT_RETRY_DELAY,
                exceptions=(Exception,)
            )
            
            # 更新结果
            node_result.status = ExecutionStatus.SUCCESS
            node_result.message = "执行成功"
            node_result.output = execution_result.get("output", {})
            node_result.metadata = execution_result.get("metadata", {})
            node_result.duration = time.time() - start_time
            
            # 更新上下文
            if execution_result.get("context_updates"):
                context.update(execution_result["context_updates"])
            
            logger.info(f"节点 {node_id} 执行成功，耗时: {node_result.duration:.3f}秒")
            
            # 触发节点完成事件
            if self.on_node_complete:
                self.on_node_complete(node_result.to_dict())
            
            metrics.nodes_executed += 1
            metrics.successful_nodes += 1
            metrics.completed_nodes.add(node_id)
            
            return node_result
            
        except Exception as e:
            node_result.status = ExecutionStatus.FAILED
            node_result.message = f"执行失败: {str(e)}"
            node_result.error = str(e)
            node_result.duration = time.time() - start_time
            
            # 记录错误
            error_info = {
                "node_id": node_id,
                "node_type": node.node_type,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "parameters": node.parameters
            }
            errors.append(error_info)
            
            logger.error(f"节点 {node_id} 执行失败: {str(e)}", exc_info=True)
            
            # 触发节点错误事件
            if self.on_node_error:
                self.on_node_error(node_result.to_dict())
            
            metrics.nodes_executed += 1
            metrics.failed_nodes += 1
            metrics.completed_nodes.add(node_id)
            
            return node_result

    async def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        """评估条件表达式
        
        注意：这里使用简单的条件评估，避免使用eval()等不安全方法
        实际项目中应该使用安全的表达式评估库
        """
        try:
            if condition.startswith("${") and condition.endswith("}"):
                var_name = condition[2:-1].strip()
                value = context.get_variable(var_name)
                if value is None:
                    value = context.get(var_name)
                if value is None:
                    context_data = context.get("variables", {})
                    value = context_data.get(var_name)
                return bool(value)
            else:
                return bool(condition)
        except Exception as e:
            logger.warning(f"条件评估失败: {condition}, 错误: {str(e)}")
            return False

    async def execute_single_node(
        self,
        node_type: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行单个节点（用于测试和调试）
        
        Args:
            node_type: 节点类型
            parameters: 节点参数
            context: 执行上下文
            
        Returns:
            执行结果
        """
        # 创建虚拟节点
        node = FlowNodeIR(
            id="single_node",
            node_type=node_type,
            parameters=parameters,
            metadata={"name": "Single Node Execution"}
        )
        
        # 创建节点实例
        node_instance = self.node_factory.create_node(node)
        if not node_instance:
            raise ExecutionError(f"无法创建节点实例: {node_type}")
        
        # 执行节点
        start_time = time.time()
        try:
            result = await node_instance.execute(parameters, context or {})
            duration = time.time() - start_time
            
            return {
                "success": True,
                "node_type": node_type,
                "output": result.get("output", {}),
                "metadata": result.get("metadata", {}),
                "duration": duration,
                "context_updates": result.get("context_updates", {})
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "node_type": node_type,
                "error": str(e),
                "duration": duration
            }

    def get_available_node_types(self) -> List[Dict[str, Any]]:
        """获取可用的节点类型信息"""
        node_types = []
        
        for node_type, entry in self.registry.get_all_nodes().items():
            if isinstance(entry, tuple):
                spec, node_class = entry
            else:
                node_class = entry
                spec = None
            
            node_info = {
                "type": node_type,
                "name": getattr(node_class, "NODE_NAME", spec.name if spec else node_type),
                "description": getattr(node_class, "NODE_DESCRIPTION", spec.description if spec else ""),
                "category": getattr(node_class, "NODE_CATEGORY", spec.category if spec else "unknown"),
                "parameters_schema": getattr(node_class, "PARAMETERS_SCHEMA", {}),
                "supports_retry": getattr(node_class, "SUPPORTS_RETRY", True),
                "timeout": getattr(node_class, "DEFAULT_TIMEOUT", 30)
            }
            node_types.append(node_info)
        
        return node_types