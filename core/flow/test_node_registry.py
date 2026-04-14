"""
测试节点注册表
管理所有可用测试节点类型的注册和查询

重构版本 - 分离定义和执行：
- _nodes: node_type -> (NodeSpec, BaseTestNode class)
"""
from typing import Dict, Type, List, Any, Optional, Tuple
import importlib
import inspect

from shared.exceptions import ValidationError
from shared.utils.logging_utils import get_logger
from shared.constants import NodeType

from .node_spec import NodeSpec, ParameterSpec

logger = get_logger(__name__)


class TestNodeRegistry:
    """
    测试节点类型注册表

    核心存储结构（原子性存储，避免不一致）：
    - _nodes: node_type -> (NodeSpec, executor_class)

    所有其他查询方法都从核心存储派生
    """

    def __init__(self):
        self._nodes: Dict[str, Tuple[NodeSpec, Type]] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, spec: NodeSpec, executor_class: Type) -> None:
        """
        注册节点类型

        Args:
            spec: 节点规格说明（必须提供）
            executor_class: 节点执行器类

        Raises:
            ValidationError: spec 为 None 或 spec.node_type 为空
        """
        if spec is None:
            raise ValidationError("NodeSpec必须提供")

        if not spec.node_type:
            raise ValidationError("NodeSpec.node_type不能为空")

        node_name = spec.node_type.lower()
        
        # 检查是否已注册
        if node_name in self._nodes:
            logger.warning(f"节点类型已注册，将覆盖: {node_name}")
        
        # 注册节点
        self._nodes[node_name] = (spec, executor_class)
        
        # 更新分类索引
        category = spec.category or "unknown"
        if category not in self._categories:
            self._categories[category] = []
        
        if node_name not in self._categories[category]:
            self._categories[category].append(node_name)

        logger.info(
            f"注册节点类型: {node_name} "
            f"(类: {executor_class.__name__}) "
            f"分类: {category}"
        )

    def unregister(self, node_name: str) -> bool:
        """
        注销节点类型

        Args:
            node_name: 节点名称

        Returns:
            是否成功注销
        """
        node_name = node_name.lower()
        
        if node_name not in self._nodes:
            logger.warning(f"节点类型未找到: {node_name}")
            return False

        # 从分类索引中移除
        spec, _ = self._nodes[node_name]
        category = spec.category or "unknown"
        if category in self._categories and node_name in self._categories[category]:
            self._categories[category].remove(node_name)
            if not self._categories[category]:
                del self._categories[category]

        # 从主注册表中移除
        del self._nodes[node_name]
        logger.info(f"注销节点类型: {node_name}")
        return True

    def get_node_class(self, node_name: str) -> Optional[Type]:
        """
        获取节点执行器类

        Args:
            node_name: 节点名称

        Returns:
            节点执行器类
        """
        entry = self._nodes.get(node_name.lower())
        return entry[1] if entry else None

    def get_node_spec(self, node_name: str) -> Optional[NodeSpec]:
        """
        获取节点规格

        Args:
            node_name: 节点名称

        Returns:
            节点规格说明
        """
        entry = self._nodes.get(node_name.lower())
        return entry[0] if entry else None

    def get_spec_and_executor(self, node_name: str) -> Optional[Tuple[NodeSpec, Type]]:
        """
        获取节点规格和执行器类

        Args:
            node_name: 节点名称

        Returns:
            (NodeSpec, executor_class) 元组
        """
        return self._nodes.get(node_name.lower())

    def get_node_names(self) -> List[str]:
        """
        获取所有注册的节点名称

        Returns:
            节点名称列表
        """
        return list(self._nodes.keys())

    def get_nodes_by_category(self, category: str) -> List[str]:
        """
        获取指定分类的节点名称

        Args:
            category: 分类名称

        Returns:
            节点名称列表
        """
        return self._categories.get(category, []).copy()

    def get_all_categories(self) -> List[str]:
        """
        获取所有分类

        Returns:
            分类名称列表
        """
        return list(self._categories.keys())

    def get_all_nodes(self) -> Dict[str, Tuple[NodeSpec, Type]]:
        """
        获取所有注册的节点

        Returns:
            节点名称到(规格, 类)的字典
        """
        return self._nodes.copy()

    def register_node(self, node_type: str, node_class: Type):
        """
        Register a node type
        
        Args:
            node_type: 节点类型名称
            node_class: 节点执行器类
        """
        # 创建默认规格
        spec = NodeSpec(
            node_type=node_type,
            name=node_type.replace('_', ' ').title(),
            description=f"Node for {node_type}",
            category="unknown"
        )
        self.register(spec, node_class)
    
    def validate_node_type(self, node_type: str) -> bool:
        """
        验证节点类型是否已注册

        Args:
            node_type: 节点类型

        Returns:
            是否已注册
        """
        return node_type.lower() in self._nodes

    def get_node_info(self, node_type: str) -> Optional[Dict[str, Any]]:
        """
        获取节点详细信息

        Args:
            node_type: 节点类型

        Returns:
            节点信息字典
        """
        entry = self._nodes.get(node_type.lower())
        if not entry:
            return None
        
        spec, executor_class = entry
        
        required_params = [p.name for p in spec.inputs if p.required]
        optional_params = [p.name for p in spec.inputs if not p.required]
        param_types = {p.name: p.type for p in spec.inputs}
        
        info = {
            "type": spec.node_type,
            "name": spec.name,
            "description": spec.description,
            "category": spec.category,
            "required_parameters": required_params,
            "optional_parameters": optional_params,
            "parameter_types": param_types,
            "executor_class": executor_class.__name__,
            "executor_module": executor_class.__module__,
            "supports_retry": getattr(executor_class, "SUPPORTS_RETRY", True),
            "default_timeout": getattr(executor_class, "DEFAULT_TIMEOUT", 30)
        }
        
        return info

    def get_all_node_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有节点的详细信息

        Returns:
            节点类型到节点信息的字典
        """
        return {
            node_type: self.get_node_info(node_type)
            for node_type in self.get_node_names()
        }

    def load_from_module(self, module_name: str) -> int:
        """
        从模块加载节点

        Args:
            module_name: 模块名称

        Returns:
            加载的节点数量
        """
        try:
            module = importlib.import_module(module_name)
            loaded_count = 0
            
            for name, obj in inspect.getmembers(module):
                # 检查是否是类且有NODE_TYPE属性
                if inspect.isclass(obj) and hasattr(obj, "NODE_TYPE"):
                    node_type = getattr(obj, "NODE_TYPE")
                    
                    # 从类属性创建ParameterSpec列表
                    required_params = getattr(obj, "REQUIRED_PARAMETERS", [])
                    optional_params = getattr(obj, "OPTIONAL_PARAMETERS", [])
                    param_types = getattr(obj, "PARAMETER_TYPES", {})
                    
                    inputs = []
                    for param in required_params:
                        inputs.append(ParameterSpec(
                            name=param,
                            type=param_types.get(param, "string"),
                            description=f"{param} parameter",
                            required=True
                        ))
                    for param in optional_params:
                        inputs.append(ParameterSpec(
                            name=param,
                            type=param_types.get(param, "string"),
                            description=f"{param} parameter",
                            required=False
                        ))
                    
                    # 创建NodeSpec
                    spec = NodeSpec(
                        node_type=node_type,
                        name=getattr(obj, "NODE_NAME", node_type),
                        description=getattr(obj, "NODE_DESCRIPTION", ""),
                        category=getattr(obj, "NODE_CATEGORY", "unknown"),
                        inputs=inputs
                    )
                    
                    # 注册节点
                    self.register(spec, obj)
                    loaded_count += 1
            
            logger.info(f"从模块 {module_name} 加载了 {loaded_count} 个节点")
            return loaded_count
            
        except ImportError as e:
            logger.error(f"导入模块失败 {module_name}: {e}")
            return 0
        except Exception as e:
            logger.error(f"从模块加载节点失败 {module_name}: {e}", exc_info=True)
            return 0

    def clear(self):
        """清空注册表"""
        self._nodes.clear()
        self._categories.clear()
        logger.info("注册表已清空")


# 全局注册表实例
global_node_registry = TestNodeRegistry()


def register_node(spec: NodeSpec, executor_class: Type):
    """
    注册节点的便捷函数

    Args:
        spec: 节点规格
        executor_class: 节点执行器类
    """
    global_node_registry.register(spec, executor_class)


def get_node_class(node_type: str) -> Optional[Type]:
    """
    获取节点类的便捷函数

    Args:
        node_type: 节点类型

    Returns:
        节点类
    """
    return global_node_registry.get_node_class(node_type)


def get_node_spec(node_type: str) -> Optional[NodeSpec]:
    """
    获取节点规格的便捷函数

    Args:
        node_type: 节点类型

    Returns:
        节点规格
    """
    return global_node_registry.get_node_spec(node_type)


def get_all_node_types() -> List[str]:
    """
    获取所有节点类型的便捷函数

    Returns:
        节点类型列表
    """
    return global_node_registry.get_node_names()


def validate_node_type(node_type: str) -> bool:
    """
    验证节点类型的便捷函数

    Args:
        node_type: 节点类型

    Returns:
        是否有效
    """
    return global_node_registry.validate_node_type(node_type)