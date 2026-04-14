import React from 'react';
import { Form, Input, Select } from 'antd';

const { TextArea } = Input;
const { Option } = Select;

const FlowProperties = ({ node, onNodeUpdate }) => {
  const [form] = Form.useForm();

  const handleValuesChange = (changedValues, allValues) => {
    if (onNodeUpdate) {
      onNodeUpdate({
        ...node,
        metadata: {
          ...node.metadata,
          name: allValues.name,
          description: allValues.description
        },
        parameters: {
          ...node.parameters,
          ...Object.fromEntries(
            Object.entries(allValues).filter(([key]) => !['name', 'description', 'on_success', 'on_failure', 'condition'].includes(key))
          )
        },
        on_success: allValues.on_success,
        on_failure: allValues.on_failure,
        condition: allValues.condition
      });
    }
  };

  const getParameterInputs = () => {
    const inputs = [];

    switch (node.node_type) {
      case 'api_test':
        inputs.push(
          <Form.Item
            key="url"
            name="url"
            label="API URL"
            rules={[{ required: true, message: '请输入API URL' }]}
          >
            <Input placeholder="https://api.example.com/users" />
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="method"
            name="method"
            label="HTTP Method"
          >
            <Select defaultValue="GET">
              <Option value="GET">GET</Option>
              <Option value="POST">POST</Option>
              <Option value="PUT">PUT</Option>
              <Option value="DELETE">DELETE</Option>
            </Select>
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="body"
            name="body"
            label="请求体"
          >
            <TextArea rows={4} placeholder='{"name": "test"}' />
          </Form.Item>
        );
        break;

      case 'ui_test':
        inputs.push(
          <Form.Item
            key="url"
            name="url"
            label="页面URL"
            rules={[{ required: true, message: '请输入页面URL' }]}
          >
            <Input placeholder="https://example.com/login" />
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="action"
            name="action"
            label="操作类型"
          >
            <Select defaultValue="goto">
              <Option value="goto">跳转</Option>
              <Option value="click">点击</Option>
              <Option value="fill">填写</Option>
              <Option value="assert">断言</Option>
            </Select>
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="selector"
            name="selector"
            label="选择器"
          >
            <Input placeholder="#username" />
          </Form.Item>
        );
        break;

      case 'data_generation':
        inputs.push(
          <Form.Item
            key="data_type"
            name="data_type"
            label="数据类型"
          >
            <Select defaultValue="string">
              <Option value="string">字符串</Option>
              <Option value="number">数字</Option>
              <Option value="boolean">布尔值</Option>
              <Option value="email">邮箱</Option>
              <Option value="phone">电话</Option>
            </Select>
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="count"
            name="count"
            label="数量"
          >
            <Input type="number" defaultValue={1} />
          </Form.Item>
        );
        break;

      case 'validation':
        inputs.push(
          <Form.Item
            key="assertion_type"
            name="assertion_type"
            label="断言类型"
          >
            <Select defaultValue="equals">
              <Option value="equals">等于</Option>
              <Option value="contains">包含</Option>
              <Option value="greater_than">大于</Option>
              <Option value="less_than">小于</Option>
            </Select>
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="expected_value"
            name="expected_value"
            label="期望值"
          >
            <Input />
          </Form.Item>
        );
        break;

      case 'report':
        inputs.push(
          <Form.Item
            key="report_type"
            name="report_type"
            label="报告类型"
          >
            <Select defaultValue="json">
              <Option value="json">JSON</Option>
              <Option value="html">HTML</Option>
              <Option value="markdown">Markdown</Option>
            </Select>
          </Form.Item>
        );
        inputs.push(
          <Form.Item
            key="report_name"
            name="report_name"
            label="报告名称"
          >
            <Input placeholder="测试报告" />
          </Form.Item>
        );
        break;

      default:
        // 默认情况，不添加任何输入项
        break;
    }

    return inputs;
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        name: node.metadata?.name || '未命名节点',
        description: node.metadata?.description || '',
        on_success: node.on_success,
        on_failure: node.on_failure,
        condition: node.condition,
        ...node.parameters
      }}
      onValuesChange={handleValuesChange}
    >
      <Form.Item
        name="name"
        label="节点名称"
        rules={[{ required: true, message: '请输入节点名称' }]}
      >
        <Input placeholder="输入节点名称" />
      </Form.Item>

      <Form.Item
        name="description"
        label="节点描述"
      >
        <TextArea rows={2} placeholder="输入节点描述" />
      </Form.Item>

      <Form.Item
        name="on_success"
        label="成功后执行节点"
      >
        <Input placeholder="输入节点ID" />
      </Form.Item>

      <Form.Item
        name="on_failure"
        label="失败后执行节点"
      >
        <Input placeholder="输入节点ID" />
      </Form.Item>

      <Form.Item
        name="condition"
        label="条件表达式"
      >
        <Input placeholder="例如: context['success'] === true" />
      </Form.Item>

      {getParameterInputs()}
    </Form>
  );
};

export default FlowProperties;
