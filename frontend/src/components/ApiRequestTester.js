import React, { useReducer, useEffect, useCallback, useState, useRef } from 'react';
import apiClient from '../api/axios';
import {
  Form,
  Input,
  Button,
  Select,
  Table,
  Card,
  Space,
  Typography,
  Row,
  Col,
  Tag,
  notification,
  Modal,
  Popconfirm,
  Descriptions,
} from 'antd';
import { usePermissions } from '../hooks/usePermissions';
import ExecutionLogModal from './ExecutionLogModal';

const { Title } = Typography;
const { Option } = Select;

/**
 * 解析并校验 headers 输入 - 只接受标准 JSON 格式
 * @param {string} input - 用户输入的 headers
 * @returns {object} - 解析后的 headers 对象
 * @throws {Error} - 如果不是标准 JSON 格式
 */
function parseHeadersInput(input) {
  if (!input || typeof input !== 'string') return {};
  
  const trimmed = input.trim();
  if (!trimmed) return {};
  
  // 只接受 JSON 格式
  if (!trimmed.startsWith('{')) {
    throw new Error('请求头格式错误：请使用标准 JSON 格式，例如 {"Content-Type": "application/json"}');
  }
  
  try {
    const parsed = JSON.parse(trimmed);
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      // 校验每个键值都是字符串
      for (const [key, value] of Object.entries(parsed)) {
        if (typeof key !== 'string' || typeof value !== 'string') {
          throw new Error('请求头格式错误：键和值都必须是字符串');
        }
      }
      return parsed;
    } else {
      throw new Error('请求头格式错误：必须是 JSON 对象格式');
    }
  } catch (e) {
    if (e.message.includes('请求头格式错误')) {
      throw e;
    }
    throw new Error('请求头格式错误：JSON 解析失败，请检查格式是否正确');
  }
}

const initialState = {
  requests: [],
  projects: [],
  loading: true,
  testingIds: new Set(), // 改为存储正在测试的请求ID
};

function reducer(state, action) {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true };
    case 'FETCH_SUCCESS':
      return { 
        ...state, 
        loading: false, 
        requests: action.payload.requests, 
        projects: action.payload.projects 
      };
    case 'FETCH_ERROR':
      return { ...state, loading: false };
    case 'TEST_START':
      return {
        ...state,
        testingIds: new Set([...state.testingIds, action.payload]), // 添加请求ID
        execModalData: {
          status: 'running',
          totalCount: 1,
          passedCount: 0,
          failedCount: 0,
        }
      };
    case 'TEST_SUCCESS':
      return {
        ...state,
        testingIds: new Set([...state.testingIds].filter(id => id !== action.payload.requestId)), // 移除请求ID
        execModalData: action.payload.result
      };
    case 'TEST_ERROR':
      return {
        ...state,
        testingIds: new Set([...state.testingIds].filter(id => id !== action.payload)) // 移除请求ID
      };
    default:
      throw new Error();
  }
}

function ApiRequestTester() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { requests, projects, loading, testingIds, execModalData } = state;
  const [form] = Form.useForm();
  const [assertionForm] = Form.useForm();
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [assertions, setAssertions] = useState([]);
  const [showAssertionModal, setShowAssertionModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [requestDetails, setRequestDetails] = useState({});
  const [editingRequest, setEditingRequest] = useState(null);
  const [editingAssertion, setEditingAssertion] = useState(null);
  const { hasCrudPermission } = usePermissions();
  
  // 执行结果弹窗状态
  const [execModalVisible, setExecModalVisible] = useState(false);
  const execRequestNameRef = useRef('');

  // 同时获取请求列表和项目列表
  const fetchData = useCallback(async () => {
    dispatch({ type: 'FETCH_START' });
    try {
      const [requestsRes, projectsRes] = await Promise.all([
        apiClient.get('/api-requests/'),
        apiClient.get('/projects/')
      ]);
      dispatch({
        type: 'FETCH_SUCCESS',
        payload: {
          requests: requestsRes.data.results || [],
          projects: projectsRes.data.results || []
        }
      });
    } catch (error) {
      notification.error({ message: '获取数据失败', description: error.message });
      dispatch({ type: 'FETCH_ERROR' });
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onFinish = async (values) => {
    try {
      const headers = parseHeadersInput(values.headers);

      await apiClient.post('/api-requests/', {
        name: values.name,
        url: values.url,
        method: values.method,
        headers: JSON.stringify(headers),
        body: values.body || '',
        project: values.project || null,
      });
      notification.success({ message: '请求已保存' });
      fetchData();
      form.resetFields();
    } catch (error) {
      notification.error({ message: '创建API请求失败', description: error.message });
    }
  };

  const handleEditRequest = (request) => {
    setEditingRequest(request);
    setShowEditModal(true);
    form.setFieldsValue({
      name: request.name,
      url: request.url,
      method: request.method,
      headers: request.headers,
      body: request.body || '',
      project: request.project,
    });
  };

  const handleUpdateRequest = async (values) => {
    if (!editingRequest) return;

    try {
      const headers = parseHeadersInput(values.headers);

      await apiClient.patch(`/api-requests/${editingRequest.id}/`, {
        name: values.name,
        url: values.url,
        method: values.method,
        headers: JSON.stringify(headers),
        body: values.body || '',
      });
      notification.success({ message: '请求已更新' });
      setShowEditModal(false);
      setEditingRequest(null);
      form.resetFields();
      fetchData();
    } catch (error) {
      notification.error({ message: '更新API请求失败', description: error.message });
    }
  };

  const handleDeleteRequest = async (requestId) => {
    try {
      await apiClient.delete(`/api-requests/${requestId}/`);
      notification.success({ message: 'API请求已删除' });
      fetchData();
    } catch (error) {
      notification.error({ message: '删除API请求失败', description: error.message });
    }
  };

  const handleTestRequest = async (requestId) => {
    // 找到请求名称
    const request = requests.find(r => r.id === requestId);
    execRequestNameRef.current = request?.name || 'API 请求';
    
    dispatch({ type: 'TEST_START', payload: requestId });
    
    // 打开弹窗，显示执行中状态
    setExecModalVisible(true);
    
    try {
      // 使用后端优化后的同步执行API，直接返回结果
      const response = await apiClient.post(`/api-requests/${requestId}/execute/`);
      const data = response.data;
      
      // 执行同步执行的优化后，所有结果直接在响应中获得
      // 执行状态、响应数据、断言结果等都在一个响应包中
      dispatch({ 
        type: 'TEST_SUCCESS', 
        payload: { 
          requestId, 
          result: {
            status: data.error_message ? 'failed' : 'passed', // 执行状态
            totalCount: 1,
            passedCount: data.passed_count || 0,
            failedCount: Math.max((data.total_assertions || 0) - (data.passed_count || 0), 0),
            responseStatus: data.response_status,
            responseTime: data.response_time,
            executionDuration: data.response_time,
            responseBody: data.response_body,
            assertions: data.assertions || [],
            logs: data.api_logs || `======= ${data.status || '开始执行'} =======\n${data.api_logs || data.response_body || JSON.stringify(data)}`,
            errorMessage: data.error_message,
            startTime: new Date().toISOString(),
            endTime: new Date().toISOString()
          } 
        } 
      });
      
      notification[data.error_message ? 'error' : 'success']({ 
        message: data.error_message ? '测试失败' : '测试成功',
        description: data.error_message || `${data.passed_count || 0}/${data.total_assertions || 0}个断言通过`
      });
    } catch (error) {
      console.error('[Frontend] 请求失败:', error);
      const errorData = {
        status: 'failed', 
        totalCount: 1,
        passedCount: 0, 
        failedCount: 1,
        logs: `[${new Date().toISOString()}] 执行测试失败: ${error.message || error}`,
        errorMessage: error.message || error.toString(),
        startTime: new Date().toISOString(),
        endTime: new Date().toISOString()
      };
      dispatch({ type: 'TEST_SUCCESS', payload: { requestId, result: errorData } });
      notification.error({ message: '测试API请求失败', description: error.message });
    }
  };

  // 关闭执行结果弹窗
  const closeExecModal = useCallback(() => {
    setExecModalVisible(false);
  }, []);

  const handleManageAssertions = async (request) => {
    setSelectedRequest(request);
    setShowAssertionModal(true);
    assertionForm.resetFields();

    // 获取该请求的断言
    try {
      const response = await apiClient.get(`/api-assertions/?api_request=${request.id}`);
      setAssertions(response.data.results || []);
      setRequestDetails(request);
    } catch (error) {
      notification.error({ message: '获取断言失败', description: error.message });
    }
  };

  const handleAddAssertion = async (values) => {
    if (!selectedRequest) return;

    // 检查是否已存在相同类型的断言
    const existingAssertion = assertions.find(
      a => a.assertion_type === values.assertion_type
    );
    
    if (existingAssertion) {
      notification.warning({ 
        message: '添加断言失败', 
        description: `该API请求已存在类型为"${getAssertionTypeName(values.assertion_type)}"的断言，不能重复添加相同类型的断言。` 
      });
      return;
    }

    try {
      await apiClient.post('/api-assertions/', {
        api_request: selectedRequest.id,
        assertion_type: values.assertion_type,
        field_path: values.field_path || '',
        comparison: values.comparison,
        expected_value: values.expected_value,
      });

      notification.success({ message: '断言已添加' });
      assertionForm.resetFields();

      // 刷新断言列表
      const response = await apiClient.get(`/api-assertions/?api_request=${selectedRequest.id}`);
      setAssertions(response.data.results || []);
    } catch (error) {
      notification.error({ message: '添加断言失败', description: error.message });
    }
  };

  // 获取断言类型的中文名称
  const getAssertionTypeName = (type) => {
    const typeMap = {
      status_code: '状态码',
      response_body: '响应体',
      response_header: '响应头',
      response_time: '响应时间',
    };
    return typeMap[type] || type;
  };

  const handleDeleteAssertion = async (assertionId) => {
    try {
      await apiClient.delete(`/api-assertions/${assertionId}/`);
      notification.success({ message: '断言已删除' });

      // 刷新断言列表
      const response = await apiClient.get(`/api-assertions/?api_request=${selectedRequest.id}`);
      setAssertions(response.data.results || []);
    } catch (error) {
      notification.error({ message: '删除断言失败', description: error.message });
    }
  };

  const handleEditAssertion = (assertion) => {
    setEditingAssertion(assertion);
    assertionForm.setFieldsValue({
      assertion_type: assertion.assertion_type,
      comparison: assertion.comparison,
      expected_value: assertion.expected_value,
      field_path: assertion.field_path || assertion.field || '',  // 兼容旧字段名field
    });
  };

  const handleUpdateAssertion = async (values) => {
    if (!editingAssertion || !selectedRequest) return;

    // 检查是否修改为已存在的断言类型（排除当前正在编辑的断言）
    const existingAssertion = assertions.find(
      a => a.assertion_type === values.assertion_type && a.id !== editingAssertion.id
    );
    
    if (existingAssertion) {
      notification.warning({ 
        message: '更新断言失败', 
        description: `该API请求已存在类型为"${getAssertionTypeName(values.assertion_type)}"的断言，不能重复添加相同类型的断言。` 
      });
      return;
    }

    try {
      await apiClient.patch(`/api-assertions/${editingAssertion.id}/`, {
        api_request: selectedRequest.id,
        assertion_type: values.assertion_type,
        field_path: values.field_path || '',
        comparison: values.comparison,
        expected_value: values.expected_value,
      });

      notification.success({ message: '断言已更新' });
      assertionForm.resetFields();
      setEditingAssertion(null);

      // 刷新断言列表
      const response = await apiClient.get(`/api-assertions/?api_request=${selectedRequest.id}`);
      setAssertions(response.data.results || []);
    } catch (error) {
      notification.error({ message: '更新断言失败', description: error.message });
    }
  };

  const handleCancelEditAssertion = () => {
    assertionForm.resetFields();
    setEditingAssertion(null);
  };

  // 优化的表格列定义
  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    { 
      title: '方法', 
      dataIndex: 'method', 
      key: 'method', 
      render: method => <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : 'volcano'}>{method}</Tag> 
    },
    {
      title: '所属项目',
      dataIndex: 'project',
      key: 'project',
      render: (projectId) => {
        const project = projects.find(p => p.id === projectId);
        return project ? project.name : '-';
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 300,  // 增加宽度以容纳所有按钮
      fixed: 'right',  // 固定在右侧
      render: (_, record) => (
        <Space size="small" wrap>
          <Button
            size="small"
            onClick={() => handleTestRequest(record.id)}
            loading={testingIds.has(record.id)}
            type="primary"
            danger={false}
          >
            测试
          </Button>
          <Button 
            size="small" 
            onClick={() => handleManageAssertions(record)} 
            disabled={!hasCrudPermission()}
          >
            断言
          </Button>
          <Button 
            size="small" 
            onClick={() => handleEditRequest(record)} 
            disabled={!hasCrudPermission()}
          >
            修改
          </Button>
          <Popconfirm
            title="确定删除该API请求吗？"
            onConfirm={() => handleDeleteRequest(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button 
              size="small" 
              danger 
              disabled={!hasCrudPermission()}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const assertionColumns = [
    { 
      title: '断言类型', 
      dataIndex: 'assertion_type', 
      key: 'assertion_type', 
      render: type => {
        const typeMap = {
          status_code: '状态码',
          response_body_field: '响应体字段',
          response_header_field: '响应头字段',
          response_time: '响应时间',
          // 向后兼容旧类型
          response_body: '响应体',
          response_header: '响应头',
        };
        return <Tag color="blue">{typeMap[type] || type}</Tag>;
      }
    },
    {
      title: '字段路径',
      dataIndex: 'field_path',
      key: 'field_path',
      render: (path, record) => {
        // 兼容旧字段名field
        const fieldPath = path || record.field || '-';
        return fieldPath;
      }
    },
    {
      title: '比较方式',
      dataIndex: 'comparison',
      key: 'comparison',
      render: comparison => {
        const compMap = {
          equals: '等于',
          contains: '包含',
          not_contains: '不包含',
          greater_than: '大于',
          less_than: '小于',
        };
        return compMap[comparison] || comparison;
      }
    },
    { title: '期望值', dataIndex: 'expected_value', key: 'expected_value' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button size="small" onClick={() => handleEditAssertion(record)} disabled={!hasCrudPermission()}>修改</Button>
          <Button size="small" danger onClick={() => handleDeleteAssertion(record.id)} disabled={!hasCrudPermission()}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <Row gutter={24}>
      <Col span={8}>
        <Title level={3}>创建API请求</Title>
        <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ method: 'GET' }}>
          <Form.Item name="name" label="请求名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true, type: 'url' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="method" label="方法" rules={[{ required: true }]}>
            <Select>
              <Option value="GET">GET</Option>
              <Option value="POST">POST</Option>
              <Option value="PUT">PUT</Option>
              <Option value="PATCH">PATCH</Option>
              <Option value="DELETE">DELETE</Option>
            </Select>
          </Form.Item>
          <Form.Item name="project" label="所属项目">
            <Select placeholder="选择项目（可选）" allowClear>
              {projects.map(project => (
                <Option key={project.id} value={project.id}>{project.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="headers" label="请求头（JSON格式）">
            <Input.TextArea rows={4} placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}' />
          </Form.Item>
          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" disabled={!hasCrudPermission()}>保存请求</Button>
          </Form.Item>
        </Form>
      </Col>
      <Col span={16}>
        <Title level={3}>已保存的请求</Title>
        <Table 
          columns={columns} 
          dataSource={requests} 
          loading={loading} 
          rowKey="id" 
          pagination={{ pageSize: 5, showSizeChanger: true }}
          scroll={{ x: 'max-content' }}
        />

        {/* 执行结果弹窗 - 适配后端同步执行优化 */}
        <ExecutionLogModal
          visible={execModalVisible}
          onClose={closeExecModal}
          title={`API 测试执行结果 - ${execRequestNameRef.current}`}
          executionType="api"
          status={execModalData?.status || 'pending'}
          totalCount={execModalData?.totalCount || 0}
          passedCount={execModalData?.passedCount || 0}
          failedCount={execModalData?.failedCount || 0}
          executionDuration={execModalData?.executionDuration}
          responseStatus={execModalData?.responseStatus}
          responseTime={execModalData?.responseTime}
          responseBody={execModalData?.responseBody}
          logs={execModalData?.logs}
          assertionResults={execModalData?.assertions || []}
          errorMessage={execModalData?.errorMessage}
          startTime={execModalData?.startTime}
          endTime={execModalData?.endTime}
        />
      </Col>

      {/* 断言管理模态框 */}
      <Modal
        title={`断言管理 - ${requestDetails?.name || ''}`}
        width={800}
        visible={showAssertionModal}
        onCancel={() => {
          setShowAssertionModal(false);
          setSelectedRequest(null);
        }}
        footer={[
          <Button key="close" onClick={() => setShowAssertionModal(false)}>
            关闭
          </Button>
        ]}
      >
        <Card title="请求详情" size="small" style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="名称">{requestDetails?.name}</Descriptions.Item>
            <Descriptions.Item label="URL">{requestDetails?.url}</Descriptions.Item>
            <Descriptions.Item label="方法">
              <Tag color="blue">{requestDetails?.method}</Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card title={editingAssertion ? "修改断言" : "添加断言"} size="small" style={{ marginBottom: 16 }}>
          <Form
            form={assertionForm}
            layout="vertical"
            onFinish={editingAssertion ? handleUpdateAssertion : handleAddAssertion}
          >
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="assertion_type" label="断言类型" rules={[{ required: true }]}>
                  <Select placeholder="选择断言类型">
                    <Option value="status_code">状态码</Option>
                    <Option value="response_body_field">响应体字段</Option>
                    <Option value="response_header_field">响应头字段</Option>
                    <Option value="response_time">响应时间</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="comparison" label="比较方式" rules={[{ required: true }]}>
                  <Select placeholder="选择比较方式">
                    <Option value="equals">等于</Option>
                    <Option value="contains">包含</Option>
                    <Option value="not_contains">不包含</Option>
                    <Option value="greater_than">大于</Option>
                    <Option value="less_than">小于</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="expected_value" label="期望值" rules={[{ required: true }]}>
                  <Input placeholder="输入期望值（如：200）" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.assertion_type !== currentValues.assertion_type}
            >
              {({ getFieldValue }) => {
                const assertionType = getFieldValue('assertion_type');
                const needsFieldPath = assertionType === 'response_body_field' || assertionType === 'response_header_field';
                
                return (
                  <Row gutter={16}>
                    <Col span={24}>
                      <Form.Item 
                        name="field_path" 
                        label={needsFieldPath ? "字段路径（必填）" : "字段路径"}
                        rules={[
                          {
                            required: needsFieldPath,
                            message: needsFieldPath ? '字段路径为必填项' : undefined
                          }
                        ]}
                      >
                        <Input 
                          placeholder={
                            assertionType === 'response_body_field' 
                              ? "如：data.id 或 $.data.id 或 data.list[0].name" 
                              : assertionType === 'response_header_field'
                              ? "响应头字段名，如：Content-Type"
                              : "不需要填写"
                          }
                          disabled={!needsFieldPath}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                );
              }}
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">
                {editingAssertion ? "保存" : "添加断言"}
              </Button>
              {editingAssertion && (
                <Button style={{ marginLeft: 8 }} onClick={handleCancelEditAssertion}>
                  取消
                </Button>
              )}
            </Form.Item>
          </Form>
        </Card>

        <Card title="断言列表" size="small">
          <Table
            columns={assertionColumns}
            dataSource={assertions}
            rowKey="id"
            pagination={{ pageSize: 5, showSizeChanger: true }}
            locale={{ emptyText: '暂无断言配置' }}
          />
        </Card>
      </Modal>

      {/* 修改API请求模态框 */}
      <Modal
        title="修改API请求"
        width={800}
        visible={showEditModal}
        onCancel={() => {
          setShowEditModal(false);
          setEditingRequest(null);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleUpdateRequest}
          initialValues={{ method: 'GET' }}
        >
          <Form.Item name="name" label="请求名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true, type: 'url' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="method" label="方法" rules={[{ required: true }]}>
            <Select>
              <Option value="GET">GET</Option>
              <Option value="POST">POST</Option>
              <Option value="PUT">PUT</Option>
              <Option value="PATCH">PATCH</Option>
              <Option value="DELETE">DELETE</Option>
            </Select>
          </Form.Item>
          <Form.Item name="project" label="所属项目">
            <Select placeholder="选择项目（可选）" allowClear>
              {projects.map(project => (
                <Option key={project.id} value={project.id}>{project.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="headers" label="请求头（JSON格式）">
            <Input.TextArea rows={4} placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}' />
          </Form.Item>
          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              保存修改
            </Button>
            <Button
              style={{ marginLeft: 8 }}
              onClick={() => {
                setShowEditModal(false);
                setEditingRequest(null);
                form.resetFields();
              }}
            >
              取消
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Row>
  );
}

export default ApiRequestTester;
