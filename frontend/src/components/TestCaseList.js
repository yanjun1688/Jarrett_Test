import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/axios';
import { Table, Input, Button, Space, Typography, Tag, notification, Modal, Form, Select, Tabs, Descriptions, Divider } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { handleApiError } from '../utils/errorHandler';
import FeatureTestCaseManager from './FeatureTestCaseManager';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

function parseHeadersInput(input) {
  if (!input || typeof input !== 'string') return {};
  const trimmed = input.trim();
  if (!trimmed) return {};
  if (!trimmed.startsWith('{')) {
    throw new Error('请求头格式错误：请使用标准 JSON 格式，例如 {"Content-Type": "application/json"}');
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof key !== 'string' || typeof value !== 'string') {
          throw new Error('请求头格式错误：键和值都必须是字符串');
        }
      }
      return parsed;
    }
    throw new Error('请求头格式错误：必须是 JSON 对象格式');
  } catch (e) {
    if (e.message.includes('请求头格式错误')) throw e;
    throw new Error('请求头格式错误：JSON 解析失败，请检查格式是否正确');
  }
}

function TestCaseList({ projectId }) {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('api');
  const [filter, setFilter] = useState({ project: '' });
  const [modalOpen, setModalOpen] = useState(false);
  const [editRecord, setEditRecord] = useState(null);
  const [form] = Form.useForm();
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  // 执行结果
  const [executing, setExecuting] = useState(null);
  const [execResult, setExecResult] = useState(null);
  const [execModalOpen, setExecModalOpen] = useState(false);
  const [assertions, setAssertions] = useState([]);


  const ASSERTION_TYPES = [
    { value: 'status_code', label: '状态码', pathLabel: null, pathPlaceholder: null },
    { value: 'response_time', label: '响应时间', pathLabel: null, pathPlaceholder: null },
    { value: 'jsonpath', label: 'JSONPath', pathLabel: '提取路径', pathPlaceholder: '$.data.user.name 或 $.data.items[0].id 或 $.data.items[*].id' },
    { value: 'response_header_field', label: '响应头', pathLabel: 'Header名', pathPlaceholder: 'Content-Type' },
  ];

  const COMPARISONS = [
    { value: 'equals', label: '等于' },
    { value: 'not_equals', label: '不等于' },
    { value: 'contains', label: '包含' },
    { value: 'not_contains', label: '不包含' },
    { value: 'greater_than', label: '大于' },
    { value: 'less_than', label: '小于' },
  ];


  const fetchTestCases = useCallback(async (searchFilter = null) => {
    setLoading(true);
    try {
      const currentFilter = searchFilter !== null ? searchFilter : { project: projectId || '' };

      if (activeTab === 'api') {
        let apiRequestUrl = '/api-requests/';
        const apiRequestParams = new URLSearchParams();

        if (currentFilter.project) {
          apiRequestParams.append('project', currentFilter.project);
        }

        const apiRequestQueryString = apiRequestParams.toString();
        if (apiRequestQueryString) {
          apiRequestUrl += `?${apiRequestQueryString}`;
        }

        const apiRequestsRes = await apiClient.get(apiRequestUrl);

        const allTestCases = (apiRequestsRes.data.results || []).map(item => ({
          ...item,
          test_type: 'api',
          project_name: item.project_name || item.project?.name,
        }));

        allTestCases.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setTestCases(allTestCases);
      } else {
        // 功能测试用例通过 FeatureTestCaseManager 组件管理，直接显示即可
        setTestCases([]);
      }
    } catch (error) {
      notification.error({ message: '获取测试用例失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId, activeTab]);

  useEffect(() => {
    fetchTestCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, activeTab]);

  useEffect(() => {
    const fetchProjects = async () => {
      setProjectsLoading(true);
      try {
        const response = await apiClient.get('/projects/');
        setProjects(response.data.results || []);
      } catch (error) {
        notification.error({ message: '获取项目列表失败', description: error.message });
      } finally {
        setProjectsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const handleProjectChange = (value) => {
    const newFilter = { project: value || '' };
    setFilter(newFilter);
    fetchTestCases(newFilter);
  };

  const openCreateApiTestModal = () => {
    setEditRecord(null);
    setAssertions([]);
    form.resetFields();
    if (projectId) {
      form.setFieldsValue({ project: projectId });
    }
    setModalOpen(true);
  };

  const openEditApiTestModal = async (record) => {
    setEditRecord(record);
    form.setFieldsValue({
      project: record.project || record.project_id,
      name: record.name,
      url: record.url,
      method: record.method || 'GET',
      headers: record.headers || '',
      body: record.body || '',
    });
    // 获取已有断言
    try {
      const res = await apiClient.get('/api-assertions/', { params: { api_request: record.id } });
      const list = (res.data.results || []).map(a => ({
        assertion_type: a.assertion_type,
        comparison: a.comparison,
        expected_value: a.expected_value ?? '',
        field_path: a.field_path || '',
        is_critical: a.is_critical,
      }));
      setAssertions(list);
    } catch {
      setAssertions([]);
    }
    setModalOpen(true);
  };

  const handleCreateOrUpdateApiTest = async () => {
    try {
      const values = await form.validateFields();
      const headers = parseHeadersInput(values.headers);

      const payload = {
        name: values.name,
        url: values.url,
        method: values.method,
        headers: JSON.stringify(headers),
        body: values.body || '',
        project: values.project,
      };

      let apiRequestId;
      if (editRecord) {
        await apiClient.patch(`/api-requests/${editRecord.id}/`, payload);
        apiRequestId = editRecord.id;
        notification.success({ message: 'API测试用例已更新' });
      } else {
        const res = await apiClient.post('/api-requests/', payload);
        apiRequestId = res.data.id;
        notification.success({ message: 'API测试用例创建成功' });
      }

      // 清除旧断言
      const oldRes = await apiClient.get('/api-assertions/', { params: { api_request: apiRequestId } });
      for (const a of oldRes.data.results || []) {
        await apiClient.delete(`/api-assertions/${a.id}/`);
      }

      // 创建新断言
      for (const a of assertions) {
        await apiClient.post('/api-assertions/', {
          api_request: apiRequestId,
          assertion_type: a.assertion_type,
          comparison: a.comparison,
          expected_value: String(a.expected_value ?? ''),
          field_path: a.field_path || '',
          is_critical: !!a.is_critical,
        });
      }

      setModalOpen(false);
      form.resetFields();
      setAssertions([]);
      fetchTestCases(filter);
    } catch (error) {
      handleApiError(error, editRecord ? '更新API测试用例失败' : '创建API测试用例失败');
    }
  };

  const addAssertion = () => {
    setAssertions([...assertions, {
      assertion_type: 'status_code',
      comparison: 'equals',
      expected_value: '200',
      field_path: '',
      is_critical: false,
    }]);
  };

  const removeAssertion = (index) => {
    setAssertions(assertions.filter((_, i) => i !== index));
  };

  const updateAssertion = (index, field, value) => {
    const updated = [...assertions];
    updated[index] = { ...updated[index], [field]: value };
    setAssertions(updated);
  };

  const handleExecute = async (record) => {
    setExecuting(record.id);
    setExecResult(null);
    try {
      const res = await apiClient.post(`/api-requests/${record.id}/execute/`);
      setExecResult(res.data);
      setExecModalOpen(true);
    } catch (error) {
      notification.error({ message: '执行失败', description: error.response?.data?.error || error.message });
    } finally {
      setExecuting(null);
    }
  };

  const handleViewLogs = async (record) => {
    try {
      const res = await apiClient.get('/executions/', { params: { api_request: record.id } });
      const logs = res.data.results || [];
      const latest = logs.reduce((a, b) => new Date(a.executed_at) > new Date(b.executed_at) ? a : b, logs[0]);
      if (!latest) {
        notification.info({ message: '暂无执行记录' });
        return;
      }
      setExecResult(latest.api_response_data || {});
      setExecModalOpen(true);
    } catch (error) {
      notification.error({ message: '获取执行日志失败', description: error.message });
    }
  };

  const columns = React.useMemo(() => [ // eslint-disable-line
    { title: '请求名称', dataIndex: 'name', key: 'name', render: (text) => <strong>{text || '-'}</strong> },
    {
      title: '请求方法',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method) => <Tag>{method || 'GET'}</Tag>,
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      render: (text) => <Text copyable ellipsis style={{ maxWidth: 400 }}>{text || '-'}</Text>,
    },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => text ? new Date(text).toLocaleString() : '' },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => openEditApiTestModal(record)}>修改</Button>
          <Button
            type="link"
            size="small"
            loading={executing === record.id}
            onClick={() => handleExecute(record)}
          >
            执行
          </Button>
          <Button type="link" size="small" onClick={() => handleViewLogs(record)}>查看日志</Button>
        </Space>
      ),
    },
  ], [executing]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试用例列表</Title>}

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="API测试用例" key="api">
          {!projectId && (
            <Space style={{ marginBottom: 16 }}>
              <Select
                placeholder="选择项目"
                style={{ width: 200 }}
                allowClear
                value={filter.project || undefined}
                onChange={handleProjectChange}
                loading={projectsLoading}
              >
                {projects.map(p => (
                  <Select.Option key={p.id} value={p.id}>{p.name}</Select.Option>
                ))}
              </Select>
              <Button onClick={openCreateApiTestModal}>
                新增用例
              </Button>
            </Space>
          )}

          <Table
            columns={columns}
            dataSource={testCases}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 10, showSizeChanger: true }}
          />
        </TabPane>

        <TabPane tab="功能测试用例" key="feature">
          <FeatureTestCaseManager />
        </TabPane>
      </Tabs>

      <Modal
        title={editRecord ? '修改API测试用例' : '添加API测试用例'}
        open={modalOpen}
        onOk={handleCreateOrUpdateApiTest}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="project"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="请选择项目"
              loading={projectsLoading}
              disabled={projectsLoading || !!projectId}
            >
              {projects.map(project => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="name" label="请求名称" rules={[{ required: true, message: '请输入请求名称' }]}>
            <Input />
          </Form.Item>

          <Form.Item name="url" label="URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="https://api.example.com/endpoint" />
          </Form.Item>

          <Form.Item
            name="method"
            label="请求方法"
            rules={[{ required: true, message: '请选择请求方法' }]}
            initialValue="GET"
          >
            <Select>
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="PATCH">PATCH</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="headers" label="请求头（JSON格式）">
            <Input.TextArea rows={4} placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}' />
          </Form.Item>

          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>

          <Divider plain>响应断言</Divider>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {assertions.map((a, i) => {
              const typeDef = ASSERTION_TYPES.find(t => t.value === a.assertion_type);
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', background: '#fafafa', borderRadius: 6,
                  border: '1px solid #f0f0f0',
                }}>
                  <Select
                    value={a.assertion_type}
                    onChange={(v) => updateAssertion(i, 'assertion_type', v)}
                    style={{ width: 110, flexShrink: 0 }}
                    size="small"
                  >
                    {ASSERTION_TYPES.map(t => (
                      <Select.Option key={t.value} value={t.value}>{t.label}</Select.Option>
                    ))}
                  </Select>
                  {typeDef?.pathLabel ? (
                    <Input
                      value={a.field_path}
                      onChange={(e) => updateAssertion(i, 'field_path', e.target.value)}
                      placeholder={typeDef.pathPlaceholder || ''}
                      style={{ flex: 1, minWidth: 180 }}
                      size="small"
                    />
                  ) : (
                    <span style={{ flex: 1, minWidth: 180, fontSize: 12, color: '#999' }}>{typeDef?.pathPlaceholder || ''}</span>
                  )}
                  <Select
                    value={a.comparison}
                    onChange={(v) => updateAssertion(i, 'comparison', v)}
                    style={{ width: 90, flexShrink: 0 }}
                    size="small"
                  >
                    {COMPARISONS.map(c => (
                      <Select.Option key={c.value} value={c.value}>{c.label}</Select.Option>
                    ))}
                  </Select>
                  <Input
                    value={a.expected_value}
                    onChange={(e) => updateAssertion(i, 'expected_value', e.target.value)}
                    placeholder="期望值"
                    style={{ width: 110, flexShrink: 0 }}
                    size="small"
                  />
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    style={{ flexShrink: 0 }}
                    onClick={() => removeAssertion(i)}
                  />
                </div>
              );
            })}
          </div>
          <Button type="dashed" onClick={addAssertion} style={{ width: '100%', marginTop: 8 }} icon={<PlusOutlined />}>
            添加断言
          </Button>
          <Text type="secondary" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
            JSONPath 示例：<Text code>$.code</Text> 取顶层字段，<Text code>$.data.user.name</Text> 取嵌套字段，
            <Text code>$.data.items[0].id</Text> 取数组第1项，<Text code>$.data.items[*].id</Text> 取所有项的 id。
          </Text>
        </Form>
      </Modal>

      <Modal
        title="执行结果"
        open={execModalOpen}
        onCancel={() => setExecModalOpen(false)}
        footer={<Button onClick={() => setExecModalOpen(false)}>关闭</Button>}
        width={700}
        destroyOnClose
      >
        {execResult && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="状态码">{execResult.status_code ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="响应时间">{execResult.response_time ? `${execResult.response_time.toFixed(2)}s` : '-'}</Descriptions.Item>
            <Descriptions.Item label="响应体">
              <pre style={{ maxHeight: 300, overflow: 'auto', margin: 0, fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {(() => {
                  const body = execResult.response_body;
                  if (!body) return '-';
                  if (typeof body === 'object') return JSON.stringify(body, null, 2);
                  try { return JSON.stringify(JSON.parse(body), null, 2); } catch { return body; }
                })()}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="断言结果">
              {(execResult.assertions || []).map((a, i) => (
                <div key={i}>
                  <Tag color={a.passed ? 'success' : 'error'}>{a.passed ? '通过' : '失败'}</Tag>
                  {a.error || `${a.assertion_type}: 预期=${a.expected_value} 实际=${a.actual_value}`}
                </div>
              )) || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>


    </Space>
  );
}

export default TestCaseList;
