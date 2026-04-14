import React from 'react';
import { Select, Input, InputNumber, Button, Space, Card } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';

const ACTION_TYPES = [
  { value: 'set_variable', label: '设置变量' },
  { value: 'delay', label: '延迟等待' },
];

const PreActionConfig = ({ value = [], onChange }) => {
  const addAction = () => {
    onChange([...value, { type: 'set_variable', config: { key: '', value: '' } }]);
  };

  const removeAction = (index) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const updateAction = (index, field, newValue) => {
    const updated = [...value];
    if (field === 'type') {
      updated[index] = {
        type: newValue,
        config: newValue === 'delay' ? { duration: 1000 } : { key: '', value: '' },
      };
    } else {
      updated[index] = {
        ...updated[index],
        config: { ...updated[index].config, [field]: newValue },
      };
    }
    onChange(updated);
  };

  return (
    <div>
      {value.length === 0 && (
        <div style={{ color: '#999', marginBottom: 8 }}>暂无前置操作</div>
      )}
      
      {value.map((action, index) => (
        <Card
          key={index}
          size="small"
          style={{ marginBottom: 8 }}
          title={
            <Select
              value={action.type}
              onChange={(v) => updateAction(index, 'type', v)}
              options={ACTION_TYPES}
              style={{ width: 120 }}
              size="small"
            />
          }
          extra={
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => removeAction(index)}
            />
          }
        >
          {action.type === 'set_variable' && (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <span style={{ width: 60 }}>变量名:</span>
                <Input
                  value={action.config.key}
                  onChange={(e) => updateAction(index, 'key', e.target.value)}
                  placeholder="变量名"
                  style={{ width: 150 }}
                  size="small"
                />
              </Space>
              <Space>
                <span style={{ width: 60 }}>变量值:</span>
                <Input
                  value={action.config.value}
                  onChange={(e) => updateAction(index, 'value', e.target.value)}
                  placeholder="支持 {{变量名}} 引用"
                  style={{ width: 250 }}
                  size="small"
                />
              </Space>
            </Space>
          )}
          
          {action.type === 'delay' && (
            <Space>
              <span>延迟时间:</span>
              <InputNumber
                value={action.config.duration}
                onChange={(v) => updateAction(index, 'duration', v || 1000)}
                min={0}
                max={60000}
                style={{ width: 100 }}
                size="small"
                addonAfter="ms"
              />
            </Space>
          )}
        </Card>
      ))}
      
      <Button type="dashed" onClick={addAction} icon={<PlusOutlined />} size="small">
        添加前置操作
      </Button>
    </div>
  );
};

export default PreActionConfig;