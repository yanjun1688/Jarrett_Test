"""
核心流程引擎模块 - 数据结构层
仅保留 FlowIR/FlowNodeIR 数据结构，用于测试流程描述
"""
from .flow_ir import FlowIR, FlowNodeIR

__all__ = [
    'FlowIR',
    'FlowNodeIR',
]