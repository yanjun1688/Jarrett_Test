import React from 'react';
import { Input, Button, Row, Col, Tooltip, Space } from 'antd';
import { PlusOutlined, DeleteOutlined, CheckOutlined, CloseOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { JSONPath } from 'jsonpath-plus';

const ExtractRulesModalContent = ({ value = [], onChange, sampleData }) => {
  const addRule = () => {
    onChange([...value, { name: '', jsonpath: '' }]);
  };

  const removeRule = (index) => {
    const newValue = value.filter((_, i) => i !== index);
    onChange(newValue);
  };

  const updateRule = (index, field, newValue) => {
    const updated = [...value];
    updated[index] = { ...updated[index], [field]: newValue };
    onChange(updated);
  };

  const testJsonPath = (jsonpath) => {
    if (!jsonpath || !sampleData) return null;
    try {
      const result = JSONPath({ path: jsonpath, json: sampleData });
      return result && result.length > 0 ? result[0] : null;
    } catch (e) {
      return null;
    }
  };

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 8, fontWeight: 'bold' }} align="middle">
        <Col span={6} style={{ paddingLeft: '14px' }}>变量名</Col>
        <Col span={11} style={{ paddingLeft: '14px' }}>JSONPath 表达式</Col>
        <Col span={4} style={{ paddingLeft: '14px' }}>测试结果</Col>
        <Col span={3} style={{ textAlign: 'center' }}>操作</Col>
      </Row>
      
      {value.map((rule, index) => {
        const testResult = testJsonPath(rule.jsonpath);
        const hasSample = !!sampleData;
        
        return (
          <Row key={index} gutter={8} style={{ marginBottom: 8, background: '#fafafa', padding: '8px', borderRadius: 4 }} align="middle">
            <Col span={6}>
              <Input
                value={rule.name}
                onChange={(e) => updateRule(index, 'name', e.target.value)}
                placeholder="变量名"
                addonBefore="{{"
                addonAfter="}}"
                size="small"
                status={rule.name && !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(rule.name) ? 'error' : ''}
              />
            </Col>
            <Col span={11}>
              <Input
                value={rule.jsonpath}
                onChange={(e) => updateRule(index, 'jsonpath', e.target.value)}
                placeholder="$.data.token"
                size="small"
                suffix={
                  <Tooltip title="参考上方示例使用正确的JSONPath语法">
                    <InfoCircleOutlined style={{ color: '#ccc' }} />
                  </Tooltip>
                }
              />
            </Col>
            <Col span={4}>
              {!hasSample ? (
                <Tooltip title="当前没有示例数据可用于测试">
                  <span style={{ color: '#ccc', fontSize: 14 }}>-</span>
                </Tooltip>
              ) : testResult !== null ? (
                <Tooltip title={`提取结果: ${JSON.stringify(testResult)}`}>
                  <Space>
                    <CheckOutlined style={{ color: '#52c41a' }} />
                    <span style={{ color: '#52c41a', fontSize: 12 }}>
                      {typeof testResult === 'object' 
                        ? JSON.stringify(testResult).substring(0, 15) + '...' 
                        : String(testResult).substring(0, 15)}
                    </span>
                  </Space>
                </Tooltip>
              ) : (
                <Tooltip title="表达式无效或未匹配到数据">
                  <CloseOutlined style={{ color: '#ff4d4f' }} />
                </Tooltip>
              )}
            </Col>
            <Col span={3} style={{ textAlign: 'center' }}>
              <DeleteOutlined
                onClick={() => removeRule(index)}
                style={{ color: '#ff4d4f', cursor: 'pointer' }}
                title="删除此规则"
              />
            </Col>
          </Row>
        );
      })}
      
      <Button type="dashed" onClick={addRule} block style={{ marginTop: 8 }} icon={<PlusOutlined />}>
        添加提取规则
      </Button>
    </div>
  );
};

export default ExtractRulesModalContent;