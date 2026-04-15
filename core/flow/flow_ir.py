"""
Flow Intermediate Representation (Flow IR)

This module defines the intermediate representation for test flows that agents
generate and modify. The IR is separate from the execution operators (BaseTestNode)
and contains all the control flow logic.

This is the unified intermediate representation for the flow framework.
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
import uuid
import json

from shared.exceptions import ValidationError
from shared.constants import TestType, NodeType, ExecutionStatus


@dataclass
class FlowNodeIR:
    """
    Flow Node Intermediate Representation - the core structure that agents operate on

    Attributes:
        id: Unique identifier for the node
        node_type: Type of the node (corresponds to BaseTestNode.NODE_TYPE)
        parameters: Configuration parameters for the node
        depends_on: List of node IDs that this node depends on (data dependencies)
        on_success: Next node to execute if this node succeeds (None = end)
        on_failure: Next node to execute if this node fails (None = end)
        condition: Optional condition for executing this node
        metadata: Additional metadata for the node
    """
    id: str = field(default="")
    node_type: str = field(default="")
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize default values"""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # 设置默认元数据
        if "name" not in self.metadata:
            self.metadata["name"] = f"Node {self.id[:8]}"
        if "description" not in self.metadata:
            self.metadata["description"] = ""
        if "category" not in self.metadata:
            self.metadata["category"] = NodeType.get_category(self.node_type)

    def validate(self) -> List[str]:
        """验证节点有效性
        
        Returns:
            错误消息列表，空列表表示验证通过
        """
        errors = []
        
        # 验证ID
        if not self.id or not isinstance(self.id, str):
            errors.append("节点ID不能为空且必须是字符串")
        
        # 验证节点类型
        if not self.node_type or not isinstance(self.node_type, str):
            errors.append("节点类型不能为空且必须是字符串")
        
        # 验证参数
        if not isinstance(self.parameters, dict):
            errors.append("参数必须是字典类型")  # type: ignore[unreachable]
        
        # 验证依赖关系
        if not isinstance(self.depends_on, list):
            errors.append("依赖关系必须是列表类型")  # type: ignore[unreachable]
        else:
            for dep in self.depends_on:
                if not isinstance(dep, str):
                    errors.append(f"依赖项必须是字符串: {dep}")  # type: ignore[unreachable]
        
        # 验证元数据
        if not isinstance(self.metadata, dict):
            errors.append("元数据必须是字典类型")  # type: ignore[unreachable]
        
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "node_type": self.node_type,
            "parameters": self.parameters,
            "depends_on": self.depends_on,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "condition": self.condition,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowNodeIR':
        """Create from dictionary representation"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            node_type=data.get("node_type", ""),
            parameters=data.get("parameters", {}),
            depends_on=data.get("depends_on", []),
            on_success=data.get("on_success"),
            on_failure=data.get("on_failure"),
            condition=data.get("condition"),
            metadata=data.get("metadata", {})
        )

    def clone(self) -> 'FlowNodeIR':
        """创建节点的深拷贝"""
        return FlowNodeIR(
            id=str(uuid.uuid4()),
            node_type=self.node_type,
            parameters=self.parameters.copy(),
            depends_on=self.depends_on.copy(),
            on_success=self.on_success,
            on_failure=self.on_failure,
            condition=self.condition,
            metadata=self.metadata.copy()
        )


@dataclass
class FlowIR:
    """
    Complete Flow Intermediate Representation

    Attributes:
        nodes: Dictionary of node ID to FlowNodeIR
        start_node: ID of the starting node
        metadata: Additional flow metadata
        version: Flow version
    """
    nodes: Dict[str, FlowNodeIR] = field(default_factory=dict)
    start_node: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Initialize default values"""
        # 如果没有节点但有起始节点，清除起始节点
        if not self.nodes and self.start_node:
            self.start_node = None
        
        # 设置默认元数据
        if "name" not in self.metadata:
            self.metadata["name"] = "Untitled Flow"
        if "description" not in self.metadata:
            self.metadata["description"] = ""
        if "test_type" not in self.metadata:
            self.metadata["test_type"] = TestType.AUTO
        if "created_at" not in self.metadata:
            from datetime import datetime
            self.metadata["created_at"] = datetime.now().isoformat()
        
        # 如果没有起始节点但有节点，设置第一个节点为起始节点
        if not self.start_node and self.nodes:
            self.start_node = next(iter(self.nodes.keys()))

    def validate(self, strict: bool = True) -> Dict[str, List[str]]:
        """验证流程有效性
        
        Args:
            strict: 是否严格验证（检查循环依赖等）
            
        Returns:
            验证结果字典: {"errors": [], "warnings": []}
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        # 验证节点
        if not self.nodes:
            errors.append("流程不能为空")
            return {"errors": errors, "warnings": warnings}
        
        # 验证起始节点
        if not self.start_node:
            errors.append("缺少起始节点")
        elif self.start_node not in self.nodes:
            errors.append(f"起始节点不存在: {self.start_node}")
        
        # 验证每个节点
        node_errors = {}
        for node_id, node in self.nodes.items():
            node_validation = node.validate()
            if node_validation:
                node_errors[node_id] = node_validation
        
        if node_errors:
            for node_id, errs in node_errors.items():
                for err in errs:
                    errors.append(f"节点 {node_id}: {err}")
        
        # 验证节点引用
        all_node_ids = set(self.nodes.keys())
        for node_id, node in self.nodes.items():
            # 验证依赖关系
            for dep in node.depends_on:
                if dep not in all_node_ids:
                    errors.append(f"节点 {node_id}: 依赖的节点不存在: {dep}")
            
            # 验证成功/失败跳转
            if node.on_success and node.on_success not in all_node_ids:
                errors.append(f"节点 {node_id}: 成功跳转的节点不存在: {node.on_success}")
            if node.on_failure and node.on_failure not in all_node_ids:
                errors.append(f"节点 {node_id}: 失败跳转的节点不存在: {node.on_failure}")
        
        # 严格验证：检查循环依赖
        if strict and not errors:
            if self._has_cycle():
                errors.append("检测到循环依赖")
        
        # 警告：孤立节点
        if not errors:
            reachable = self._get_reachable_nodes()
            unreachable = all_node_ids - reachable
            if unreachable:
                warnings.append(f"存在孤立节点: {', '.join(unreachable)}")
        
        return {"errors": errors, "warnings": warnings}

    def _has_cycle(self) -> bool:
        """检查是否存在循环（分别检测依赖环和跳转环）"""
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            node = self.nodes[node_id]
            # 检查依赖关系（反向边）
            for dep in node.depends_on:
                if dep in self.nodes and dfs(dep):
                    return True
            # 检查跳转关系（正向边）
            for next_node in [node.on_success, node.on_failure]:
                if next_node and next_node in self.nodes:
                    if dfs(next_node):
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False

    def _get_reachable_nodes(self) -> Set[str]:
        """获取从起始节点可达的所有节点"""
        if not self.start_node:
            return set()
        
        visited = set()
        stack = [self.start_node]
        
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            # 添加依赖节点
            for dep in node.depends_on:
                if dep not in visited:
                    stack.append(dep)
            
            # 添加跳转节点
            for next_node in [node.on_success, node.on_failure]:
                if next_node and next_node not in visited:
                    stack.append(next_node)
        
        return visited

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "start_node": self.start_node,
            "metadata": self.metadata,
            "version": self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowIR':
        """Create from dictionary representation"""
        nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            nodes[node_id] = FlowNodeIR.from_dict(node_data)
        
        return cls(
            nodes=nodes,
            start_node=data.get("start_node"),
            metadata=data.get("metadata", {}),
            version=data.get("version", "1.0.0")
        )

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'FlowIR':
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_node(self, node: FlowNodeIR) -> None:
        """添加节点"""
        self.nodes[node.id] = node
        
        # 如果没有起始节点，设置此节点为起始节点
        if not self.start_node:
            self.start_node = node.id

    def remove_node(self, node_id: str) -> bool:
        """移除节点
        
        Returns:
            是否成功移除
        """
        if node_id not in self.nodes:
            return False
        
        # 更新其他节点的引用
        for node in self.nodes.values():
            if node.on_success == node_id:
                node.on_success = None
            if node.on_failure == node_id:
                node.on_failure = None
            if node_id in node.depends_on:
                node.depends_on.remove(node_id)
        
        # 如果移除的是起始节点，重新设置起始节点
        if self.start_node == node_id:
            remaining_nodes = [nid for nid in self.nodes.keys() if nid != node_id]
            self.start_node = remaining_nodes[0] if remaining_nodes else None
        
        # 移除节点
        del self.nodes[node_id]
        return True

    def get_execution_order(self) -> List[str]:
        """获取执行顺序
        
        Returns:
            节点ID列表，按执行顺序排列
        """
        if not self.start_node:
            return []
        
        # 使用拓扑排序
        visited = set()
        result = []
        
        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id not in self.nodes:
                return
            
            visited.add(node_id)
            node = self.nodes[node_id]
            
            # 先访问依赖节点
            for dep in node.depends_on:
                visit(dep)
            
            result.append(node_id)
            
            # 访问成功跳转节点
            if node.on_success:
                visit(node.on_success)
            
            # 访问依赖于当前节点的节点
            for nid, n in self.nodes.items():
                if node_id in n.depends_on and nid not in visited:
                    visit(nid)
        
        visit(self.start_node)
        return result

    def clone(self) -> 'FlowIR':
        """创建流程的深拷贝"""
        cloned_nodes = {}
        for node_id, node in self.nodes.items():
            cloned_nodes[node_id] = node.clone()
        
        return FlowIR(
            nodes=cloned_nodes,
            start_node=self.start_node,
            metadata=self.metadata.copy(),
            version=self.version
        )

    def get_node(self, node_id: str) -> Optional[FlowNodeIR]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def get_statistics(self) -> Dict[str, Any]:
        """获取流程统计信息"""
        node_types: Dict[str, int] = {}
        for node in self.nodes.values():
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "node_types": node_types,
            "has_condition": any(node.condition for node in self.nodes.values()),
            "has_parallel": any(len(node.depends_on) > 1 for node in self.nodes.values()),
            "test_type": self.metadata.get("test_type", TestType.AUTO),
            "reachable_nodes": len(self._get_reachable_nodes())
        }