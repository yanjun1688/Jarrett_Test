"""
Execution Metrics

This module defines metrics for node and flow execution.
Separated from flow_models.py for better organization.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set
import time
from datetime import datetime

from shared.constants import ExecutionStatus


@dataclass
class NodeExecutionResult:
    """节点执行结果（标准化格式）"""
    node_id: str
    node_type: str
    status: str = ExecutionStatus.PENDING
    message: str = ""
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.end_time is not None and self.start_time is not None:
            self.duration = self.end_time - self.start_time
    
    def mark_started(self):
        """标记开始执行"""
        self.start_time = time.time()
        self.status = ExecutionStatus.RUNNING
    
    def mark_completed(self, success: bool = True, message: str = "", output: Optional[Dict[str, Any]] = None):
        """标记执行完成"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
        self.message = message
        self.output = output or {}
    
    def mark_failed(self, error: str, message: str = ""):
        """标记执行失败"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = ExecutionStatus.FAILED
        self.error = error
        self.message = message or f"执行失败: {error}"
    
    def mark_skipped(self, reason: str = ""):
        """标记跳过执行"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = ExecutionStatus.SKIPPED
        self.message = reason or "跳过执行"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "status": self.status,
            "message": self.message,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeExecutionResult':
        """从字典创建"""
        result = cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            status=data.get("status", ExecutionStatus.PENDING),
            message=data.get("message", ""),
            output=data.get("output"),
            error=data.get("error"),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            metadata=data.get("metadata", {})
        )
        result.duration = data.get("duration", 0.0)
        return result


@dataclass
class FlowExecutionMetrics:
    """流程执行指标"""
    nodes_executed: int = 0
    successful_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    total_duration: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = ExecutionStatus.PENDING
    completed_nodes: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.end_time is not None and self.start_time is not None:
            self.total_duration = self.end_time - self.start_time
    
    def mark_started(self):
        """标记开始执行"""
        self.start_time = time.time()
        self.status = ExecutionStatus.RUNNING
    
    def mark_completed(self, success: bool = True):
        """标记执行完成"""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        self.status = ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED
    
    def mark_failed(self):
        """标记执行失败"""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        self.status = ExecutionStatus.FAILED
    
    def mark_timeout(self):
        """标记执行超时"""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        self.status = ExecutionStatus.TIMEOUT
    
    def add_node_result(self, result: NodeExecutionResult):
        """添加节点执行结果"""
        self.nodes_executed += 1
        self.completed_nodes.add(result.node_id)
        
        if result.status == ExecutionStatus.SUCCESS:
            self.successful_nodes += 1
        elif result.status == ExecutionStatus.FAILED:
            self.failed_nodes += 1
        elif result.status == ExecutionStatus.SKIPPED:
            self.skipped_nodes += 1
    
    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, 
                              ExecutionStatus.CANCELLED, ExecutionStatus.TIMEOUT]
    
    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self.status == ExecutionStatus.RUNNING
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.nodes_executed == 0:
            return 0.0
        return self.successful_nodes / self.nodes_executed
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        if self.nodes_executed == 0:
            return 0.0
        return self.failed_nodes / self.nodes_executed
    
    @property
    def average_node_duration(self) -> float:
        """平均节点执行时间"""
        if self.nodes_executed == 0:
            return 0.0
        return self.total_duration / self.nodes_executed
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes_executed": self.nodes_executed,
            "successful_nodes": self.successful_nodes,
            "failed_nodes": self.failed_nodes,
            "skipped_nodes": self.skipped_nodes,
            "total_duration": self.total_duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "completed_nodes": list(self.completed_nodes),
            "is_completed": self.is_completed,
            "is_running": self.is_running,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_node_duration": self.average_node_duration,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlowExecutionMetrics':
        """从字典创建"""
        metrics = cls(
            nodes_executed=data.get("nodes_executed", 0),
            successful_nodes=data.get("successful_nodes", 0),
            failed_nodes=data.get("failed_nodes", 0),
            skipped_nodes=data.get("skipped_nodes", 0),
            total_duration=data.get("total_duration", 0.0),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            status=data.get("status", ExecutionStatus.PENDING)
        )
        metrics.completed_nodes = set(data.get("completed_nodes", []))
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "status": self.status,
            "total_nodes": self.nodes_executed,
            "successful": self.successful_nodes,
            "failed": self.failed_nodes,
            "skipped": self.skipped_nodes,
            "success_rate": f"{self.success_rate:.1%}",
            "total_duration": f"{self.total_duration:.2f}秒",
            "average_duration": f"{self.average_node_duration:.2f}秒/节点"
        }


class ExecutionStatistics:
    """执行统计"""
    
    def __init__(self):
        self.flow_metrics: Dict[str, FlowExecutionMetrics] = {}
        self.node_metrics: Dict[str, Dict[str, Any]] = {}
        self.start_time = time.time()
    
    def add_flow_metrics(self, flow_id: str, metrics: FlowExecutionMetrics):
        """添加流程指标"""
        self.flow_metrics[flow_id] = metrics
    
    def add_node_metrics(self, node_type: str, duration: float, success: bool):
        """添加节点指标"""
        if node_type not in self.node_metrics:
            self.node_metrics[node_type] = {
                "count": 0,
                "success_count": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0
            }
        
        stats = self.node_metrics[node_type]
        stats["count"] += 1
        stats["total_duration"] += duration
        
        if success:
            stats["success_count"] += 1
        
        if duration < stats["min_duration"]:
            stats["min_duration"] = duration
        
        if duration > stats["max_duration"]:
            stats["max_duration"] = duration
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        total_flows = len(self.flow_metrics)
        successful_flows = sum(1 for m in self.flow_metrics.values() if m.status == ExecutionStatus.SUCCESS)
        
        total_nodes = sum(m.nodes_executed for m in self.flow_metrics.values())
        successful_nodes = sum(m.successful_nodes for m in self.flow_metrics.values())
        
        node_type_stats = {}
        for node_type, stats in self.node_metrics.items():
            node_type_stats[node_type] = {
                "count": stats["count"],
                "success_rate": stats["success_count"] / stats["count"] if stats["count"] > 0 else 0,
                "avg_duration": stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0,
                "min_duration": stats["min_duration"] if stats["min_duration"] != float('inf') else 0,
                "max_duration": stats["max_duration"]
            }
        
        return {
            "total_flows": total_flows,
            "successful_flows": successful_flows,
            "flow_success_rate": successful_flows / total_flows if total_flows > 0 else 0,
            "total_nodes": total_nodes,
            "successful_nodes": successful_nodes,
            "node_success_rate": successful_nodes / total_nodes if total_nodes > 0 else 0,
            "node_type_stats": node_type_stats,
            "collection_duration": time.time() - self.start_time
        }