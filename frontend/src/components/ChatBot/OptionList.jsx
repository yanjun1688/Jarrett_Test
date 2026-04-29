/**
 * ChatBot 选项列表组件
 * 用于渲染工具返回的选项列表（如项目选择、PRD文档选择）
 */
import React from 'react';
import { List, Card, Typography } from 'antd';

const { Text } = Typography;

const OptionList = ({ options, title, onSelect }) => {
  if (!options || options.length === 0) return null;

  return (
    <Card 
      size="small" 
      title={title || '请选择：'}
      style={{ marginBottom: 12 }}
      bodyStyle={{ padding: '8px 0' }}
    >
      <List
        size="small"
        dataSource={options}
        renderItem={(item, index) => (
          <List.Item
            key={item.id || index}
            onClick={() => onSelect?.(item)}
            style={{ 
              cursor: 'pointer', 
              padding: '8px 12px',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <List.Item.Meta
              title={<Text strong>{item.label}</Text>}
              description={item.description && (
                <Text type="secondary" ellipsis>
                  {item.description}
                </Text>
              )}
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

export default React.memo(OptionList);