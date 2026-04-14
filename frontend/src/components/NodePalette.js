import React from 'react';
import { List, Space, Tooltip } from 'antd';
import { ApiOutlined, PlayCircleOutlined, DatabaseOutlined, CheckCircleOutlined, FileTextOutlined } from '@ant-design/icons';

const nodeTypes = [
  {
    type: 'api_test',
    name: 'API测试节点',
    description: '发送HTTP请求并验证响应',
    icon: <ApiOutlined />,
    category: 'API'
  },
  {
    type: 'ui_test',
    name: 'UI测试节点',
    description: '模拟用户操作浏览器页面',
    icon: <PlayCircleOutlined />,
    category: 'UI'
  },
  {
    type: 'data_generation',
    name: '数据生成节点',
    description: '生成测试数据',
    icon: <DatabaseOutlined />,
    category: '数据'
  },
  {
    type: 'validation',
    name: '验证节点',
    description: '验证数据或状态',
    icon: <CheckCircleOutlined />,
    category: '验证'
  },
  {
    type: 'report',
    name: '报告节点',
    description: '生成测试报告',
    icon: <FileTextOutlined />,
    category: '报告'
  }
];

const NodePalette = () => {
  return (
    <div>
      {Object.entries(nodeTypes.reduce((acc, node) => {
        if (!acc[node.category]) {
          acc[node.category] = [];
        }
        acc[node.category].push(node);
        return acc;
      }, {})).map(([category, nodes]) => (
        <div key={category} style={{ marginBottom: 16 }}>
          <h4 style={{ marginBottom: 8, fontSize: '12px', color: '#666' }}>
            {category}
          </h4>
          <List
            dataSource={nodes}
            renderItem={(node) => (
              <List.Item
                key={node.type}
                style={{
                  cursor: 'pointer',
                  padding: '8px 12px',
                  borderRadius: 4,
                  marginBottom: 4,
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#f0f5ff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                <Tooltip title={node.description}>
                  <Space>
                    {node.icon}
                    <span style={{ fontSize: '12px' }}>{node.name}</span>
                  </Space>
                </Tooltip>
              </List.Item>
            )}
          />
        </div>
      ))}
    </div>
  );
};

export default NodePalette;
