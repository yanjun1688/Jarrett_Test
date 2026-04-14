import React from 'react';
import { Select, Input, Button, Space, Card, Tag, Tooltip, InputNumber, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';

const ASSERTION_TYPES = [
  { value: 'status_code', label: '状态码验证' },
  { value: 'response_time', label: '响应时间验证' },
  { value: 'jsonpath', label: 'JSONPath验证' },
  { value: 'header', label: 'Header验证' },
];

const OPERATORS = [
  { value: 'equals', label: '等于' },
  { value: 'not_equals', label: '不等于' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'greater_than', label: '大于' },
  { value: 'less_than', label: '小于' },
];

const AssertionConfig = ({ value = [], onChange }) => {
  const addAssertion = () => {
    onChange([...value, { type: 'status_code', operator: 'equals', expected: '200', path: '' }]);
  };

  const removeAssertion = (index) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const updateAssertion = (index, field, newValue) => {
    const updated = [...value];
    updated[index] = { ...updated[index], [field]: newValue };
    onChange(updated);
  };

  const renderAssertionFields = (assertion, index) => {
    switch (assertion.type) {
      case 'status_code':
        return (
          <Space>
            <span>期望状态码:</span>
            <InputNumber
              value={assertion.expected}
              onChange={(v) => updateAssertion(index, 'expected', String(v || 200))}
              min={100}
              max={599}
              style={{ width: 80 }}
              size="small"
            />
          </Space>
        );
      
      case 'response_time':
        return (
          <Space>
            <Select
              value={assertion.operator || 'less_than'}
              onChange={(v) => updateAssertion(index, 'operator', v)}
              options={OPERATORS.filter(o => ['less_than', 'greater_than'].includes(o.value))}
              style={{ width: 100 }}
              size="small"
            />
            <InputNumber
              value={assertion.expected}
              onChange={(v) => updateAssertion(index, 'expected', String(v || 1000))}
              min={0}
              style={{ width: 80 }}
              size="small"
              addonAfter="ms"
            />
          </Space>
        );
      
      case 'jsonpath':
        return (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <span>JSONPath:</span>
              <Input
                value={assertion.path}
                onChange={(e) => updateAssertion(index, 'path', e.target.value)}
                placeholder="$.data.id"
                style={{ width: 150 }}
                size="small"
                suffix={
                  <Tooltip title="使用 JSONPath 提取响应字段">
                    <InfoCircleOutlined style={{ color: '#ccc' }} />
                  </Tooltip>
                }
              />
            </Space>
            <Space>
              <Select
                value={assertion.operator || 'equals'}
                onChange={(v) => updateAssertion(index, 'operator', v)}
                options={OPERATORS}
                style={{ width: 100 }}
                size="small"
              />
              <Input
                value={assertion.expected}
                onChange={(e) => updateAssertion(index, 'expected', e.target.value)}
                placeholder="期望值"
                style={{ width: 150 }}
                size="small"
              />
            </Space>
          </Space>
        );
      
      case 'header':
        return (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <span>Header名:</span>
              <Input
                value={assertion.path}
                onChange={(e) => updateAssertion(index, 'path', e.target.value)}
                placeholder="Content-Type"
                style={{ width: 150 }}
                size="small"
              />
            </Space>
            <Space>
              <Select
                value={assertion.operator || 'contains'}
                onChange={(v) => updateAssertion(index, 'operator', v)}
                options={OPERATORS.filter(o => ['equals', 'contains'].includes(o.value))}
                style={{ width: 100 }}
                size="small"
              />
              <Input
                value={assertion.expected}
                onChange={(e) => updateAssertion(index, 'expected', e.target.value)}
                placeholder="期望值"
                style={{ width: 150 }}
                size="small"
              />
            </Space>
          </Space>
        );
      
      default:
        return null;
    }
  };

  return (
    <div>
      {value.length === 0 && (
        <div style={{ color: '#999', marginBottom: 8 }}>暂无断言规则</div>
      )}
      
      {value.map((assertion, index) => (
        <Card
          key={index}
          size="small"
          style={{ marginBottom: 8, position: 'relative' }}
        >
          <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
            <Popconfirm
              title="确定删除此断言?"
              onConfirm={() => removeAssertion(index)}
              okText="删除"
              cancelText="取消"
            >
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </div>
          <Space style={{ width: '100%', marginTop: 24 }}>
            <Tag color="blue">{ASSERTION_TYPES.find(t => t.value === assertion.type)?.label || assertion.type}</Tag>
            <Select
              value={assertion.type}
              onChange={(v) => updateAssertion(index, 'type', v)}
              options={ASSERTION_TYPES}
              style={{ width: 140 }}
              size="small"
            />
            {renderAssertionFields(assertion, index)}
          </Space>
        </Card>
      ))}
      
      <Button type="dashed" onClick={addAssertion} icon={<PlusOutlined />} size="small">
        添加断言
      </Button>
    </div>
  );
};

export default AssertionConfig;