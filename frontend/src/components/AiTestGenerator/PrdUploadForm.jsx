import React, { useState } from 'react';
import { Form, Button, Select, Space, message, Upload, Spin, Alert } from 'antd';
import { RocketOutlined, InboxOutlined } from '@ant-design/icons';
import { testGenerationAPI } from '../../api/testGeneration';

const { Option } = Select;
const { Dragger } = Upload;

const ACCEPTED_FILE_TYPES = '.pdf,.docx,.doc,.txt,.md';
const MAX_FILE_SIZE = 10 * 1024 * 1024;

const PrdUploadForm = ({
  projects,
  loadingProjects,
  generating,
  onGenerateStart,
  onGenerateComplete,
  onGenerateError,
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState([]);

  const beforeUpload = (file) => {
    const isValidType = ACCEPTED_FILE_TYPES.split(',').some((ext) =>
      file.name.toLowerCase().endsWith(ext.trim())
    );
    if (!isValidType) {
      message.error('仅支持 PDF、Word、TXT、Markdown 格式');
      return Upload.LIST_IGNORE;
    }
    if (file.size > MAX_FILE_SIZE) {
      message.error('文件大小不能超过 10MB');
      return Upload.LIST_IGNORE;
    }
    return false;
  };

  const handleSubmit = async (values) => {
    if (fileList.length === 0) {
      message.error('请上传PRD文档');
      return;
    }

    onGenerateStart();
    try {
      const file = fileList[0].originFileObj || fileList[0];
      const formData = new FormData();
      formData.append('project_id', values.project_id);
      formData.append('file', file);
      formData.append('test_type', 'prd');
      formData.append('source', 'generator');

      const response = await testGenerationAPI.generateFromPRDFile(formData);

      const data = response.data;

      if (!data.success) {
        message.error(data.error || '分析失败');
        onGenerateError(new Error(data.error || '分析失败'));
        return;
      }

      const result = {
        success: true,
        analysis: data.response || data.analysis || '',
        document_content: file.name || '',
      };

      onGenerateComplete(result);
      message.success('分析完成');
    } catch (error) {
      onGenerateError(error);
      message.error(error.response?.data?.error || error.message || '分析失败');
    }
  };

  return (
    <Spin spinning={loadingProjects}>
      <Alert
        type="info"
        message="PRD文档分析"
        description="提交 PRD 文档后，AI 将分析文档内容并生成功能测试用例。受模型输出长度限制，超长内容可能会被截断，建议控制文档篇幅。"
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
          label="PRD文档"
          name="file"
          extra="支持 PDF、Word、TXT、Markdown 格式，最大 10MB"
        >
          <Dragger
            fileList={fileList}
            beforeUpload={beforeUpload}
            onChange={({ fileList }) => setFileList(fileList)}
            accept={ACCEPTED_FILE_TYPES}
            maxCount={1}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持 .pdf, .docx, .doc, .txt, .md 格式
            </p>
          </Dragger>
        </Form.Item>

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<RocketOutlined />}
              loading={generating}
              disabled={generating || fileList.length === 0}
            >
              开始分析
            </Button>
            <Button onClick={() => { form.resetFields(); setFileList([]); }}>
              清空
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default PrdUploadForm;