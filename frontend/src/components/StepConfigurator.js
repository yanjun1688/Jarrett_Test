import React from 'react';
import { Button, Input, Select, Form, Card, Space, Divider, InputNumber, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { v4 as uuidv4 } from 'uuid';

const { TextArea } = Input;
const { Option } = Select;

const StepConfigurator = ({ steps = [], onChange, title = "测试步骤" }) => {
  const addNewStep = () => {
    const newStep = {
      id: uuidv4(),
      name: `步骤-${steps.length + 1}`,
      request: {
        method: 'GET',
        url: '',
        headers: {},
        json: {}
      },
      extract: [],
      assertions: []
    };
    
    if (Array.isArray(steps)) {
      onChange([...steps, newStep]);
    } else {
      onChange([newStep]);
    }
  };

  const updateStep = (index, updatedStep) => {
    const updatedSteps = [...steps];
    updatedSteps[index] = { ...updatedSteps[index], ...updatedStep };
    onChange(updatedSteps);
  };

  const removeStep = (index) => {
    const updatedSteps = steps.filter((_, i) => i !== index);
    onChange(updatedSteps);
  };

  const configureStepParams = (index, params) => {
    const step = steps[index];
    const updatedStep = { ...step, ...params };
    updateStep(index, updatedStep);
  };

  const configureStepRequest = (index, requestParams) => {
    const step = steps[index];
    const updatedStep = {
      ...step,
      request: { ...step.request, ...requestParams }
    };
    updateStep(index, updatedStep);
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>{title}</h3>
        <Button 
          type="primary" 
          icon={<PlusOutlined />} 
          onClick={addNewStep}
          size="small"
        >
          添加{title.includes('步骤') ? '测试' : title.includes('设') ? '设置' : ''}步骤
        </Button>
      </div>

      {steps.map((step, index) => (
        <Card
          key={step.id || index}
          size="small"
          title={
            <Space>
              <strong>{step.name || `步骤 ${index + 1}`}</strong>
              <Tag color="blue">{step.request?.method || 'GET'}</Tag>
            </Space>
          }
          extra={
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => removeStep(index)}
              size="small"
            />
          }
          style={{ marginBottom: 16 }}
        >
          <Form layout="vertical">
            <Form.Item label="步骤名称">
              <Input
                value={step.name}
                onChange={(e) => configureStepParams(index, { name: e.target.value })}
                placeholder="例如：登录获取Token"
              />
            </Form.Item>

            <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>请求配置</Divider>
            <Form.Item label="请求方法">
              <Select
                value={step.request.method}
                onChange={(value) => configureStepRequest(index, { method: value })}
                style={{ width: '100%' }}
              >
                <Option value="GET">GET</Option>
                <Option value="POST">POST</Option>
                <Option value="PUT">PUT</Option>
                <Option value="DELETE">DELETE</Option>
                <Option value="PATCH">PATCH</Option>
              </Select>
            </Form.Item>

            <Form.Item label="请求URL">
              <Input
                value={step.request.url}
                onChange={(e) => configureStepRequest(index, { url: e.target.value })}
                placeholder="例如：{{base_url}}/api/login"
              />
            </Form.Item>

            <Form.Item label="请求头">
              <TextArea
                value={JSON.stringify(step.request.headers || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const headers = JSON.parse(e.target.value) || {};
                    configureStepRequest(index, { headers });
                  } catch (err) {
                    // Ignore errors during typing
                  }
                }}
                placeholder='{"Content-Type": "application/json"}'
                rows={2}
              />
            </Form.Item>

            <Form.Item label="请求体">
              <TextArea
                value={JSON.stringify(step.request.json || step.request.body || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const parsed = JSON.parse(e.target.value) || {};
                    configureStepRequest(index, { json: parsed });
                  } catch (err) {
                    // Ignore errors during typing
                  }
                }}
                placeholder='{"username": "{{username}}", "password": "{{password}}"}'
                rows={4}
              />
            </Form.Item>

            {/* 变量提取配置 */}
            <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>变量提取</Divider>
            {step.extract && step.extract.length > 0 && step.extract.map((extractItem, extIndex) => (
              <Card 
                size="small" 
                key={extIndex} 
                style={{ marginBottom: 8, position: 'relative' }}
              >
                <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
                  <Button 
                    type="text" 
                    danger 
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => {
                      const updatedExtract = step.extract.filter((_, i) => i !== extIndex);
                      configureStepParams(index, { extract: updatedExtract });
                    }}
                  />
                </div>
                <Form.Item label="变量名" style={{ marginTop: 24 }}>
                  <Input
                    value={extractItem.name}
                    onChange={(e) => {
                      const updatedExtract = [...step.extract];
                      updatedExtract[extIndex].name = e.target.value;
                      configureStepParams(index, { extract: updatedExtract });
                    }}
                    placeholder="例如: token"
                  />
                </Form.Item>
                <Form.Item label="JSONPath">
                  <Input
                    value={extractItem.jsonpath}
                    onChange={(e) => {
                      const updatedExtract = [...step.extract];
                      updatedExtract[extIndex].jsonpath = e.target.value;
                      configureStepParams(index, { extract: updatedExtract });
                    }}
                    placeholder="例如: $.token.data.token"
                  />
                </Form.Item>
              </Card>
            ))}

            <Button 
              size="small" 
              style={{ marginBottom: 8 }} 
              onClick={() => {
                const newExtract = { name: '', jsonpath: '' };
                const updatedExtract = step.extract ? [...step.extract, newExtract] : [newExtract];
                configureStepParams(index, { extract: updatedExtract });
              }}
            >
              <PlusOutlined /> 添加提取规则
            </Button>

            {/* 断言配置 */}
            <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>断言验证</Divider>
            {step.assertions && step.assertions.length > 0 && step.assertions.map((assertion, assertIndex) => (
              <Card 
                size="small" 
                key={assertIndex} 
                style={{ marginBottom: 8, position: 'relative' }}
              >
                <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
                  <Button 
                    type="text" 
                    danger 
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => {
                      const updatedAssertions = step.assertions.filter((_, i) => i !== assertIndex);
                      configureStepParams(index, { assertions: updatedAssertions });
                    }}
                  />
                </div>
                <Form.Item label="断言类型" style={{ marginTop: 24 }}>
                  <Select
                    value={assertion.type}
                    onChange={(value) => {
                      const updatedAssertions = [...step.assertions];
                      updatedAssertions[assertIndex].type = value;
                      configureStepParams(index, { assertions: updatedAssertions });
                    }}
                  >
                    <Option value="status_code">状态码</Option>
                    <Option value="jsonpath">JSON响应验证</Option>
                  </Select>
                </Form.Item>

                {assertion.type === 'status_code' && (
                  <Form.Item label="期望状态码">
                    <InputNumber
                      value={assertion.expected}
                      onChange={(value) => {
                        const updatedAssertions = [...step.assertions];
                        updatedAssertions[assertIndex].expected = value;
                        configureStepParams(index, { assertions: updatedAssertions });
                      }}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                )}

                {assertion.type === 'jsonpath' && (
                  <>
                    <Form.Item label="JSONPath表达式">
                      <Input
                        value={assertion.expression}
                        onChange={(e) => {
                          const updatedAssertions = [...step.assertions];
                          updatedAssertions[assertIndex].expression = e.target.value;
                          configureStepParams(index, { assertions: updatedAssertions });
                        }}
                        placeholder="例如: $.code"
                      />
                    </Form.Item>
                    <Form.Item label="期望值">
                      <Input
                        value={assertion.expected}
                        onChange={(e) => {
                          const updatedAssertions = [...step.assertions];
                          updatedAssertions[assertIndex].expected = e.target.value;
                          configureStepParams(index, { assertions: updatedAssertions });
                        }}
                        placeholder="期望的值"
                      />
                    </Form.Item>
                  </>
                )}

                {assertion.type === 'response_time' && (
                  <div style={{ color: '#999', fontStyle: 'italic' }}>
                    响应时间断言暂不支持，请使用状态码或JSON响应验证
                  </div>
                )}
              </Card>
            ))}

            <Button 
              size="small" 
              style={{ marginBottom: 8 }} 
              onClick={() => {
                const newAssertion = { type: 'status_code', expected: 200 };
                const updatedAssertions = step.assertions ? [...step.assertions, newAssertion] : [newAssertion];
                configureStepParams(index, { assertions: updatedAssertions });
              }}
            >
              <PlusOutlined /> 添加断言
            </Button>
          </Form>
        </Card>
      ))}
    </div>
  );
};

export default StepConfigurator;