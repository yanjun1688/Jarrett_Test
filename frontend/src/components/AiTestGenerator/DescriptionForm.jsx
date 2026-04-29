/**
 * @deprecated 描述生成功能已废弃。
 * 该组件通过文本描述直接调用 LLM 生成 UI 测试脚本，但从功能层面已被判定为无实际意义。
 * 保留仅用于参考，未来版本将移除。
 * 替代方案：使用「API定义」标签页通过 API 定义生成测试，或「PRD文档」标签页上传文档生成测试。
 */
import React from 'react';
import { Form, Input, Button, Select, Space, message, Spin, Alert } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import { testGenerationAPI } from '../../api/testGeneration';

const { TextArea } = Input;
const { Option } = Select;

const DescriptionForm = ({
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
      const response = await testGenerationAPI.generateUITest({
        description: values.description,
        project_id: values.project_id,
        url: values.url || undefined,
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
        type="warning"
        message="【已废弃】描述生成功能"
        description='该功能已废弃，纯文本描述生成的 UI 测试脚本实用性较低。建议使用「API定义」或「PRD文档」标签页生成测试用例。'
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
          label="测试描述"
          name="description"
          rules={[
            { required: true, message: '请输入测试描述' },
            { max: 500, message: '描述最多500字符' },
          ]}
          extra="描述测试场景，AI将生成对应的UI测试脚本"
        >
          <TextArea
            rows={6}
            placeholder="例如：用户登录流程：打开首页，点击登录按钮，输入用户名密码，点击登录"
            showCount
            maxLength={500}
          />
        </Form.Item>

        <Form.Item
          label="目标URL"
          name="url"
          extra="可选，指定测试目标页面地址"
        >
          <Input placeholder="https://example.com/login" />
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

export default DescriptionForm;
