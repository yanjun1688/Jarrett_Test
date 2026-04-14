"""
节点工厂 - 负责 FlowIR 到 Runtime 的转换

这个文件提供了 NodeFactory 类，用于将 FlowNodeIR（编译时表示）
转换为 BaseTestNode 实例（运行时）。

职责：
- 从 Registry 获取节点执行器类
- 根据节点类型和参数创建节点实例
- 验证节点类型有效性
- 验证节点参数
"""
from typing import Dict, Any, Optional

from shared.exceptions import ValidationError, ExecutionError
from shared.utils.logging_utils import get_logger

from .flow_ir import FlowNodeIR
from .test_node_registry import TestNodeRegistry
from .node_spec import NodeSpec

logger = get_logger(__name__)


class NodeFactory:
    """
    节点工厂 - 将 FlowIR 转换为可执行节点实例

    这是 IR 层和运行时层之间的唯一转换入口。

    设计原则：
    - 单一职责：只负责节点实例化
    - 不包含执行逻辑
    - 不包含流程控制逻辑
    - 提供参数验证
    """

    def __init__(self, registry: TestNodeRegistry, validate_parameters: bool = True):
        """
        初始化节点工厂

        Args:
            registry: 测试节点注册表
            validate_parameters: 是否验证节点参数（默认 True）
        """
        self.registry = registry
        self.validate_parameters = validate_parameters
        self._cache: Dict[str, Any] = {}

    def create_node(self, ir_node: FlowNodeIR) -> Any:
        """
        从 FlowIR 节点创建运行时节点实例

        这是 IR → Runtime 的核心转换点。

        Args:
            ir_node: FlowIR 节点（编译时表示）

        Returns:
            节点实例（运行时）

        Raises:
            ValidationError: 节点类型未注册或参数验证失败
            ExecutionError: 节点实例化失败
        """
        logger.debug(f"创建节点: {ir_node.id} (类型: {ir_node.node_type})")

        # 获取节点执行器类
        executor_class = self.registry.get_node_class(ir_node.node_type)
        if executor_class is None:
            available_types = self.registry.get_node_names()
            raise ValidationError(
                f"未知的节点类型: '{ir_node.node_type}'",
                details={
                    "node_id": ir_node.id,
                    "node_type": ir_node.node_type,
                    "available_types": available_types
                }
            )

        # 获取节点规格
        node_spec = self.registry.get_node_spec(ir_node.node_type)
        
        # 验证参数
        if self.validate_parameters and node_spec:
            validation_errors = node_spec.validate_parameters(ir_node.parameters)
            if validation_errors:
                raise ValidationError(
                    f"节点参数验证失败: {ir_node.id}",
                    details={
                        "node_id": ir_node.id,
                        "node_type": ir_node.node_type,
                        "errors": validation_errors,
                        "parameters": ir_node.parameters
                    }
                )

        try:
            # 创建节点实例
            # 注意：这里假设节点执行器类的构造函数接受节点ID和参数
            node_instance = executor_class(ir_node.id, ir_node.parameters)
            logger.debug(f"节点创建成功: {ir_node.id}")
            return node_instance
        except Exception as e:
            logger.error(f"创建节点失败 {ir_node.id}: {e}", exc_info=True)
            raise ExecutionError(
                f"创建节点失败: {ir_node.id}",
                node_id=ir_node.id,
                node_type=ir_node.node_type,
                details={"error": str(e), "parameters": ir_node.parameters}
            )

    def create_nodes_batch(self, flow_nodes: Dict[str, FlowNodeIR]) -> Dict[str, Any]:
        """
        批量创建节点实例

        Args:
            flow_nodes: FlowIR 节点字典

        Returns:
            节点ID到节点实例的字典

        Raises:
            ValidationError: 任何节点创建失败
        """
        nodes = {}
        errors = []
        
        for node_id, ir_node in flow_nodes.items():
            try:
                node_instance = self.create_node(ir_node)
                nodes[node_id] = node_instance
            except Exception as e:
                errors.append({
                    "node_id": node_id,
                    "node_type": ir_node.node_type,
                    "error": str(e)
                })
        
        if errors:
            raise ValidationError(
                "批量创建节点失败",
                details={"errors": errors, "successful_nodes": list(nodes.keys())}
            )
        
        return nodes

    def validate_node(self, node_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证节点类型和参数

        Args:
            node_type: 节点类型
            parameters: 节点参数

        Returns:
            验证结果: {"valid": bool, "errors": List[str], "spec": Optional[NodeSpec]}
        """
        result = {
            "valid": False,
            "errors": [],
            "spec": None,
            "node_type": node_type
        }
        
        # 检查节点类型
        executor_class = self.registry.get_node_class(node_type)
        if executor_class is None:
            result["errors"].append(f"未知的节点类型: '{node_type}'")
            return result
        
        # 获取节点规格
        node_spec = self.registry.get_node_spec(node_type)
        if not node_spec:
            result["errors"].append(f"节点类型没有规格定义: '{node_type}'")
            return result
        
        result["spec"] = node_spec
        
        # 验证参数
        validation_errors = node_spec.validate_parameters(parameters)
        if validation_errors:
            result["errors"].extend(validation_errors)
        else:
            result["valid"] = True
        
        return result

    def get_node_info(self, node_type: str) -> Optional[Dict[str, Any]]:
        """
        获取节点信息

        Args:
            node_type: 节点类型

        Returns:
            节点信息字典，如果节点类型不存在则返回None
        """
        executor_class = self.registry.get_node_class(node_type)
        if executor_class is None:
            return None
        
        node_spec = self.registry.get_node_spec(node_type)
        
        info = {
            "type": node_type,
            "class_name": executor_class.__name__,
            "module": executor_class.__module__,
            "description": getattr(executor_class, "NODE_DESCRIPTION", ""),
            "category": getattr(executor_class, "NODE_CATEGORY", "unknown"),
            "supports_retry": getattr(executor_class, "SUPPORTS_RETRY", True),
            "default_timeout": getattr(executor_class, "DEFAULT_TIMEOUT", 30),
            "parameters_schema": getattr(executor_class, "PARAMETERS_SCHEMA", {})
        }
        
        if node_spec:
            required_params = [p.name for p in node_spec.inputs if p.required]
            optional_params = [p.name for p in node_spec.inputs if not p.required]
            param_types = {p.name: p.type for p in node_spec.inputs}
            
            info["spec"] = {
                "name": node_spec.name,
                "description": node_spec.description,
                "required_parameters": required_params,
                "optional_parameters": optional_params,
                "parameter_types": param_types
            }
        
        return info

    def get_all_node_types(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有节点类型的信息

        Returns:
            节点类型到节点信息的字典
        """
        node_types = {}
        
        for node_type in self.registry.get_node_names():
            node_info = self.get_node_info(node_type)
            if node_info:
                node_types[node_type] = node_info
        
        return node_types

    def create_node_from_dict(self, node_data: Dict[str, Any]) -> Any:
        """
        从字典数据创建节点

        Args:
            node_data: 节点数据字典，必须包含 node_type 和 parameters

        Returns:
            节点实例
        """
        # 创建FlowNodeIR
        ir_node = FlowNodeIR(
            id=node_data.get("id", ""),
            node_type=node_data["node_type"],
            parameters=node_data.get("parameters", {}),
            metadata=node_data.get("metadata", {})
        )
        
        return self.create_node(ir_node)

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()