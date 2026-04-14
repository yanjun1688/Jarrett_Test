import React from 'react';
import { Button, Tooltip } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';

const FlowCanvas = ({ flow, selectedNode, onNodeSelect, onNodeDelete }) => {
  const handleNodeClick = (node) => {
    if (onNodeSelect) {
      onNodeSelect(node);
    }
  };

  const handleNodeDelete = (nodeId) => {
    if (onNodeDelete) {
      onNodeDelete(nodeId);
    }
  };

  const renderNode = (nodeId, node) => {
    const isSelected = selectedNode && selectedNode.id === nodeId;
    const isStartNode = flow.start_node === nodeId;

    return (
      <div
        key={nodeId}
        className={`flow-node ${isSelected ? 'selected' : ''} ${isStartNode ? 'start-node' : ''}`}
        style={{
          position: 'absolute',
          left: node.metadata?.position?.x || 100,
          top: node.metadata?.position?.y || 100,
          width: 200,
          padding: 12,
          borderRadius: 8,
          background: isSelected ? '#e6f7ff' : isStartNode ? '#f6ffed' : '#fff',
          border: `2px solid ${isSelected ? '#1890ff' : isStartNode ? '#52c41a' : '#d9d9d9'}`,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
          cursor: 'pointer',
          transition: 'all 0.3s',
          zIndex: isSelected ? 10 : 1
        }}
        onClick={() => handleNodeClick({ ...node, id: nodeId })}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontWeight: 'bold', fontSize: '14px' }}>
            {isStartNode && <span style={{ marginRight: 4 }}>🚀</span>}
            {node.metadata?.name || '未命名节点'}
          </span>
          <Tooltip title="删除节点">
            <Button
              type="text"
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleNodeDelete(nodeId);
              }}
              danger
            />
          </Tooltip>
        </div>
        <div style={{ fontSize: '12px', color: '#666' }}>
          类型: {node.node_type}
        </div>
        {node.condition && (
          <div style={{ fontSize: '11px', color: '#1890ff', marginTop: 4 }}>
            条件: {node.condition}
          </div>
        )}
        {node.on_success && (
          <div style={{ fontSize: '11px', color: '#52c41a', marginTop: 2 }}>
            成功: {node.on_success}
          </div>
        )}
        {node.on_failure && (
          <div style={{ fontSize: '11px', color: '#ff4d4f', marginTop: 2 }}>
            失败: {node.on_failure}
          </div>
        )}
      </div>
    );
  };

  const renderConnection = (nodeId, node) => {
    const connections = [];

    if (node.on_success) {
      connections.push({
        from: nodeId,
        to: node.on_success,
        type: 'success',
        color: '#52c41a'
      });
    }

    if (node.on_failure) {
      connections.push({
        from: nodeId,
        to: node.on_failure,
        type: 'failure',
        color: '#ff4d4f'
      });
    }

    return connections.map(conn => {
      const fromNode = flow.nodes[conn.from];
      const toNode = flow.nodes[conn.to];

      if (!fromNode || !toNode) {
        return null;
      }

      // 简化版连接渲染，实际项目中可以使用更高级的连线库
      return (
        <div
          key={`${conn.from}-${conn.to}-${conn.type}`}
          className="flow-connection"
          style={{
            position: 'absolute',
            height: '2px',
            background: conn.color,
            transformOrigin: 'left center',
            zIndex: 0
          }}
        />
      );
    });
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: 600,
        border: '1px solid #d9d9d9',
        borderRadius: 8,
        overflow: 'auto',
        background: '#fafafa'
      }}
    >
      {/* 渲染连接 */}
      {Object.entries(flow.nodes || {}).flatMap(([nodeId, node]) => renderConnection(nodeId, node))}

      {/* 渲染节点 */}
      {Object.entries(flow.nodes || {}).map(([nodeId, node]) => renderNode(nodeId, node))}

      {Object.keys(flow.nodes || {}).length === 0 && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          color: '#999',
          fontSize: '16px'
        }}>
          点击"生成流程"按钮或从节点库拖放节点到此处
        </div>
      )}
    </div>
  );
};

export default FlowCanvas;
