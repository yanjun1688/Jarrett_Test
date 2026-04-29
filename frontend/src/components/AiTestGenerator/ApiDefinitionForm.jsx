import React from 'react';
import { Form, Input, Button, Select, Space, message, Spin, Alert } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import { testGenerationAPI } from '../../api/testGeneration';

const { TextArea } = Input;
const { Option } = Select;

const ApiDefinitionForm = ({
  projects,
  loadingProjects,
  generating,
  onGenerateStart,
  onGenerateComplete,
  onGenerateError,
}) => {
  const [form] = Form.useForm();

  const handleSubmit = async (values) => {
    onGenerateStart();
    try {
      const response = await testGenerationAPI.generateAPITest({
        project_id: values.project_id,
        description: values.api_definition || `测试 ${values.method || 'GET'} ${values.endpoint}`,
        endpoint: values.endpoint,
        method: values.method || 'GET',
      });

      const data = response.data;
      
      if (!data.success) {
        message.error(data.error || '生成失败');
        onGenerateError(new Error(data.error || '生成失败'));
        return;
      }

      onGenerateComplete({
        success: true,
        markdown: data.response,
        testType: 'api',
        projectId: values.project_id,
        endpoint: values.endpoint,
        method: values.method || 'GET',
      });
      message.success('生成成功');
    } catch (error) {
      onGenerateError(error);
      message.error(error.response?.data?.error || error.message || '生成失败');
    }
  };

  return (
    <Spin spinning={loadingProjects}>
      <Alert
        type="info"
        message="API 测试生成器"
        description="输入 API 信息，AI 将生成 JSON 结构化的可执行测试配置，支持直接在系统内执行并查看断言结果。"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          label="所属项目"
          name="project_id"
          rules={[{ required: true, message: '请选择项目' }]}
        >
          <Select placeholder="请选择项目" allowClear>
            {projects.map((p) => (
              <Option key={p.id} value={p.id}>{p.name}</Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="HTTP 方法"
          name="method"
          initialValue="GET"
        >
          <Select>
            <Option value="GET">GET</Option>
            <Option value="POST">POST</Option>
            <Option value="PUT">PUT</Option>
            <Option value="DELETE">DELETE</Option>
            <Option value="PATCH">PATCH</Option>
          </Select>
        </Form.Item>

        <Form.Item
          label="API 端点"
          name="endpoint"
          rules={[{ required: true, message: '请输入API端点' }]}
          extra="例如：/api/v1/users/login"
        >
          <Input placeholder="/api/v1/users/login" />
        </Form.Item>

        <Form.Item
          label="API 定义/描述"
          name="api_definition"
          extra="可选，详细描述API的功能和参数"
        >
          <TextArea
            rows={4}
            placeholder="描述API的功能、请求参数、响应格式等..."
          />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<RocketOutlined />}
              loading={generating}
              disabled={generating}
            >
              开始生成
            </Button>
            <Button onClick={() => form.resetFields()}>
              清空
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default ApiDefinitionForm;