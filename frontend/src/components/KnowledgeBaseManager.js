import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Upload, Modal, Form, Select, Input, Space, message, Tag, Popconfirm } from 'antd';
import { UploadOutlined, DeleteOutlined, ReloadOutlined, FileTextOutlined, InboxOutlined, SyncOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { agentAPI } from '../api/agent';
import { projectsAPI } from '../api/projects';

const { Option } = Select;
const { Dragger } = Upload;

const DOC_TYPE_OPTIONS = [
  { value: 'prd', label: 'PRD文档' },
  { value: 'api_doc', label: '接口文档' },
  { value: 'feature_test', label: '功能测试用例' },
  { value: 'api_test', label: '接口测试用例' },
  { value: 'ui_test', label: 'UI测试用例' },
];

const KnowledgeBaseManager = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [syncingDocs, setSyncingDocs] = useState(new Set());
  const [form] = Form.useForm();

  useEffect(() => {
    loadProjects();
    loadDocuments();
  }, []);

  const loadProjects = async () => {
    try {
      const res = await projectsAPI.getAll();
      if (res.data && res.data.results) {
        setProjects(res.data.results);
      } else if (res.data && Array.isArray(res.data)) {
        setProjects(res.data);
      }
    } catch (error) {
      console.error('加载项目失败:', error);
    }
  };

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await agentAPI.listKnowledgeDocuments();
      if (res.data && res.data.documents) {
        setDocuments(res.data.documents);
      }
    } catch (error) {
      message.error('加载文档列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (values) => {
    setUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('project_id', values.project_id);
      formData.append('doc_type', values.doc_type);
      formData.append('title', values.title);
      
      if (values.content) {
        formData.append('content', values.content);
      }
      if (values.file && values.file.length > 0) {
        formData.append('file', values.file[0].originFileObj);
      }

      await agentAPI.uploadDocument(formData);
      message.success('上传成功');
      setUploadModalVisible(false);
      form.resetFields();
      loadDocuments();
    } catch (error) {
      message.error(error.response?.data?.error || '上传失败');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleDelete = async (record) => {
    try {
      await agentAPI.deleteKnowledgeDocument(record.id);
      message.success('删除成功');
      loadDocuments();
    } catch (error) {
      message.error('删除失败');
      console.error(error);
    }
  };

  const handleSync = async (record) => {
    setSyncingDocs(prev => new Set(prev).add(record.id));
    try {
      const res = await agentAPI.syncDocument(record.id);
      if (res.data?.success) {
        message.success(res.data.message || '同步成功');
        // 同步执行，立即刷新
        loadDocuments();
        setSyncingDocs(prev => {
          const next = new Set(prev);
          next.delete(record.id);
          return next;
        });
      } else {
        message.error(res.data?.error || '同步失败');
        setSyncingDocs(prev => {
          const next = new Set(prev);
          next.delete(record.id);
          return next;
        });
      }
    } catch (error) {
      message.error('同步失败');
      console.error(error);
      setSyncingDocs(prev => {
        const next = new Set(prev);
        next.delete(record.id);
        return next;
      });
    }
  };

  const columns = [
    {
      title: '文档标题',
      dataIndex: 'title',
      key: 'title',
      render: (text, record) => text || `${record.doc_type} - ${record.id}`,
    },
    {
      title: '类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 120,
      render: (type) => {
        const option = DOC_TYPE_OPTIONS.find(o => o.value === type);
        return option?.label || type;
      },
    },
    {
      title: '知识库',
      dataIndex: 'knowledge_base_name',
      key: 'knowledge_base_name',
      width: 180,
    },
    {
      title: '同步状态',
      dataIndex: 'sync_status',
      key: 'sync_status',
      width: 110,
      render: (status, record) => {
        const isSyncing = syncingDocs.has(record.id);
        if (isSyncing) {
          return (
            <Tag icon={<LoadingOutlined />} color="processing">
              同步中...
            </Tag>
          );
        }
        const statusMap = {
          pending: { color: 'orange', text: '待同步' },
          syncing: { color: 'processing', text: '同步中' },
          synced: { color: 'success', text: '已同步' },
          failed: { color: 'error', text: '失败' },
        };
        const info = statusMap[status] || { color: 'default', text: status || 'unknown' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => {
        const isSyncing = syncingDocs.has(record.id);
        const status = record.sync_status;
        const needSync = status === 'pending' || status === 'failed';
        
        return (
          <Space size="small">
            {needSync && !isSyncing && (
              <Button
                type="text"
                icon={<SyncOutlined />}
                onClick={() => handleSync(record)}
                size="small"
                loading={isSyncing}
                title={status === 'failed' ? '重试同步' : '立即同步'}
              >
                {status === 'failed' ? '重试' : '同步'}
              </Button>
            )}
            {isSyncing && (
              <Button
                type="text"
                icon={<LoadingOutlined spin />}
                size="small"
                disabled
              >
                同步中
              </Button>
            )}
            {status === 'synced' && !isSyncing && (
              <Tag icon={<CheckCircleOutlined />} color="success" style={{ marginRight: 8 }}>
                已同步
              </Tag>
            )}
            <Popconfirm
              title="确定删除此文档？"
              description="删除后将从知识库中移除"
              onConfirm={() => handleDelete(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                size="small"
              >
                删除
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>知识库文档管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadDocuments} loading={loading}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalVisible(true)}
            >
              上传文档
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          locale={{ emptyText: '暂无文档，请上传' }}
        />
      </Card>

      <Modal
        title="上传文档到知识库"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUpload}
          initialValues={{ doc_type: 'prd' }}
        >
          <Form.Item
            name="project_id"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select placeholder="请选择项目">
              {projects.map(p => (
                <Option key={p.id} value={p.id}>{p.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="doc_type"
            label="文档类型"
            rules={[{ required: true, message: '请选择文档类型' }]}
          >
            <Select placeholder="请选择文档类型">
              {DOC_TYPE_OPTIONS.map(o => (
                <Option key={o.value} value={o.value}>{o.label}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="title"
            label="文档标题"
            rules={[{ required: true, message: '请输入文档标题' }]}
          >
            <Input placeholder="请输入文档标题" />
          </Form.Item>

          <Form.Item
            name="uploadType"
            label="上传方式"
          >
            <Select
              placeholder="选择上传方式"
              onChange={(value) => form.setFieldValue('uploadType', value)}
            >
              <Option value="file">上传文件</Option>
              <Option value="text">直接输入文本</Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.uploadType !== curr.uploadType}
          >
            {({ getFieldValue }) => {
              const uploadType = getFieldValue('uploadType');
              if (uploadType === 'text') {
                return (
                  <Form.Item
                    name="content"
                    label="文档内容"
                    rules={[{ required: true, message: '请输入文档内容' }]}
                  >
                    <Input.TextArea rows={10} placeholder="请输入文档内容（支持Markdown格式）" />
                  </Form.Item>
                );
              }
              return (
                <Form.Item
                  name="file"
                  label="上传文件"
                  valuePropName="fileList"
                  getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList)}
                  rules={[{ required: true, message: '请上传文件' }]}
                >
                  <Dragger
                    name="file"
                    accept=".txt,.md,.json,.yaml,.yml,.pdf,.docx,.doc"
                    beforeUpload={() => false}
                    maxCount={1}
                    showUploadList
                  >
                    <p className="ant-upload-drag-icon">
                      <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                    <p className="ant-upload-hint">
                      支持 PDF、Word(.docx/.doc)、TXT、Markdown、JSON、YAML 格式
                    </p>
                  </Dragger>
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item style={{ marginTop: 24, marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setUploadModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={uploadLoading}>
                上传
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgeBaseManager;