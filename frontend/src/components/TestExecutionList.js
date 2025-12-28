import React, { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Typography, Tag, Dropdown, Menu, notification, Modal, Descriptions, Card, Form, Select, Input } from 'antd';
import { DownOutlined, PlayCircleOutlined, EyeOutlined, PlusOutlined } from '@ant-design/icons';
import { testExecutionsAPI } from '../api';
import apiClient from '../api/axios';
import { usePermissions } from '../hooks/usePermissions';

const { Title } = Typography;
const { Option } = Select;

const getStatusTag = (status) => {
  switch (status) {
    case 'passed':
      return <Tag color="success">通过</Tag>;
    case 'failed':
      return <Tag color="error">失败</Tag>;
    case 'blocked':
      return <Tag color="warning">阻塞</Tag>;
    case 'skipped':
      return <Tag color="default">跳过</Tag>;
    default:
      return <Tag>{status}</Tag>;
  }
};

const getTestTypeTag = (testType) => {
  switch (testType) {
    case 'api':
      return <Tag color="blue">API测试</Tag>;
    case 'testcase':
      return <Tag color="green">功能测试</Tag>;
    default:
      return <Tag>{testType}</Tag>;
  }
};

function TestExecutionList({ projectId }) {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState(null); // 跟踪正在执行的测试ID
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [currentLogs, setCurrentLogs] = useState([]);
  const [currentExecution, setCurrentExecution] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [testcaseList, setTestcaseList] = useState([]);
  const [apiRequestList, setApiRequestList] = useState([]);
  const [createForm] = Form.useForm();
  const { hasCrudPermission } = usePermissions();

  const fetchExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (projectId) {
        params.testcase__project = projectId;
      }
      const response = await testExecutionsAPI.getAll(params);
      setExecutions(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取执行记录失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  // 清除轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const handleStatusChange = async (executionId, newStatus) => {
    try {
      await testExecutionsAPI.patch(executionId, {
        status: newStatus,
      });
      notification.success({ message: `状态已更新为 ${newStatus}` });
      fetchExecutions();
    } catch (error) {
      notification.error({ message: '更新状态失败', description: error.message });
    }
  };

  const handleCreateExecution = () => {
    console.log('[Frontend Debug] 点击了"新建执行"按钮');
    setCreateModalVisible(true);
    console.log('[Frontend Debug] 即将调用 loadTestCasesAndApiRequests()');
    loadTestCasesAndApiRequests();
    console.log('[Frontend Debug] loadTestCasesAndApiRequests() 调用完成');
  };

  const loadTestCasesAndApiRequests = async () => {
    console.log('[Frontend Debug] 开始调用 loadTestCasesAndApiRequests()');
    console.log('[Frontend Debug] projectId:', projectId);
    const testcaseUrl = '/testcases/' + (projectId ? `?project=${projectId}` : '');
    console.log('[Frontend Debug] 准备请求的URL:');
    console.log('[Frontend Debug]   - 测试用例接口:', testcaseUrl);
    console.log('[Frontend Debug]   - API请求接口:', '/api-requests/');
    try {
      console.log('[Frontend Debug] 发起请求...');
      const [testcasesRes, apiRequestsRes] = await Promise.all([
        apiClient.get(testcaseUrl),
        apiClient.get('/api-requests/')
      ]);
      console.log('[Frontend Debug] 请求成功！');
      console.log('[Frontend Debug] 测试用例接口返回:', testcasesRes);
      console.log('[Frontend Debug] API请求接口返回:', apiRequestsRes);
      console.log('[Frontend Debug] 测试用例数据:', testcasesRes.data);
      console.log('[Frontend Debug] API请求数据:', apiRequestsRes.data);
      console.log('[Frontend Debug] 测试用例列表 results:', testcasesRes.data.results);
      console.log('[Frontend Debug] API请求列表 results:', apiRequestsRes.data.results);
      const testcases = testcasesRes.data.results || [];
      const apiRequests = apiRequestsRes.data.results || [];
      console.log('[Frontend Debug] 设置 state: testcaseList (长度:', testcases.length, ')');
      console.log('[Frontend Debug] 设置 state: apiRequestList (长度:', apiRequests.length, ')');
      setTestcaseList(testcases);
      setApiRequestList(apiRequests);
      console.log('[Frontend Debug] state 设置完成');
    } catch (error) {
      console.error('[Frontend Debug] 请求失败:', error);
      notification.error({ message: '加载数据失败', description: error.message });
    }
  };

  const handleSubmitCreate = async (values) => {
    console.log('[Frontend Debug] 提交表单数据:', values);
    try {
      const data = {
        status: 'pending',
        actual_result: '',
        comments: values.comments || ''
      };

      if (values.test_type === 'testcase') {
        data.test_type = 'testcase';
        data.testcase = values.testcase_id;
      } else {
        data.test_type = 'api';
        data.api_request = values.api_request_id;
      }

      console.log('[Frontend Debug] 准备发送到后端的数据:', data);
      console.log('[Frontend Debug] 调用 testExecutionsAPI.create()');

      await testExecutionsAPI.create(data);
      notification.success({ message: '执行记录已保存' });
      setCreateModalVisible(false);
      createForm.resetFields();
      fetchExecutions();
    } catch (error) {
      console.error('[Frontend Debug] 保存失败:', error);
      console.error('[Frontend Debug] 错误详情:', error.response);
      console.error('[Frontend Debug] 错误消息:', error.message);
      notification.error({ message: '保存失败', description: error.message });
    }
  };

  const handleExecuteApiTest = async (record) => {
    console.log('[Frontend Debug] ==================== 开始执行测试 ====================');
    console.log('[Frontend Debug] 执行记录:', record);

    if (record.test_type !== 'api' || !record.api_request) {
      notification.warning({ message: '只能执行API测试类型' });
      return;
    }

    // 防止重复点击
    if (executingId === record.id) {
      return;
    }

    setExecutingId(record.id);

    try {
      setCurrentExecution(record);
      setCurrentLogs([]);
      setLogModalVisible(true);

      // 开始执行
      notification.info({ message: '开始执行API测试', description: '正在发送请求...' });
      console.log('[Frontend Debug] 调用 testExecutionsAPI.postAction(', record.id, ', "execute")');

      const response = await testExecutionsAPI.postAction(record.id, 'execute');

      console.log('[Frontend Debug] 执行API测试完成，返回响应对象:', response);
      console.log('[Frontend Debug] response.data:', response.data);
      console.log('[Frontend Debug] response.data.logs:', response.data?.logs);
      console.log('[Frontend Debug] response.data.logs 长度:', response.data?.logs ? response.data.logs.length : 'undefined');
      console.log('[Frontend Debug] response.data.status:', response.data?.status);
      console.log('[Frontend Debug] response.data.response_data:', response.data?.response_data);
      console.log('[Frontend Debug] response.data.execution_duration_ms:', response.data?.execution_duration_ms);

      // 更新执行记录的持续时间（毫秒）
      if (response.data?.execution_duration_ms !== undefined) {
        setCurrentExecution(prev => ({
          ...prev,
          execution_duration_ms: response.data.execution_duration_ms
        }));
      }

      // 立即显示执行返回的日志（实时日志）
      if (response.data?.logs && response.data.logs.length > 0) {
        console.log('[Frontend Debug] 设置实时日志:', response.data.logs);
        setCurrentLogs(response.data.logs);
        console.log('[Frontend Debug] setCurrentLogs 已调用');
      } else {
        console.log('[Frontend Debug] 没有收到日志或日志为空');
      }

      if (response.data?.status === 'failed') {
        console.log('[Frontend Debug] 执行失败:', response.data?.actual_result);
        notification.error({ message: '测试执行失败', description: response.data?.actual_result || '未知错误' });
      } else {
        const successMessage = response.data?.actual_result || '测试执行完成';
        console.log('[Frontend Debug] 执行成功:', successMessage);
        notification.success({ message: '测试执行完成', description: `结果: ${successMessage}` });
      }

      // 立即获取日志（从数据库获取）
      console.log('[Frontend Debug] 调用 fetchLogs(', record.id, ')');
      fetchLogs(record.id);

      // 如果是pending或running状态，开始轮询
      if (response.status === 'pending' || response.status === 'running') {
        console.log('[Frontend Debug] 状态为', response.status, '，开始轮询日志');
        startPollingLogs(record.id);
      }

      // 刷新列表
      fetchExecutions();
      console.log('[Frontend Debug] ==================== 执行完成 ====================');
    } catch (error) {
      console.error('[Frontend Debug] 执行失败:', error);
      notification.error({ message: '执行失败', description: error.message });
    } finally {
      setExecutingId(null); // 重置执行状态
    }
  };

  const startPollingLogs = (executionId) => {
    // 清除旧的轮询
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // 每2秒轮询一次
    const newInterval = setInterval(async () => {
      try {
        const response = await testExecutionsAPI.getAction(executionId, 'logs');
        console.log('[Frontend Debug] 轮询获取日志:', response.data?.logs?.length, '条');
        setCurrentLogs(response.data?.logs || []);

        // 如果执行完成，停止轮询
        if (response.data?.status !== 'pending' && response.data?.status !== 'running') {
          clearInterval(newInterval);
          setPollingInterval(null);
          notification.info({ message: '执行完成', description: 'API测试执行已完成' });
        }
      } catch (error) {
        console.error('[Frontend Debug] 轮询日志失败:', error);
        clearInterval(newInterval);
        setPollingInterval(null);
      }
    }, 2000);

    setPollingInterval(newInterval);
  };

  const fetchLogs = async (executionId) => {
    try {
      console.log('[Frontend Debug] fetchLogs() - 准备获取日志，executionId:', executionId);
      const response = await testExecutionsAPI.getAction(executionId, 'logs');
      console.log('[Frontend Debug] fetchLogs() - 收到响应:', response);
      console.log('[Frontend Debug] fetchLogs() - response.data:', response.data);
      console.log('[Frontend Debug] fetchLogs() - response.data.logs:', response.data?.logs);
      console.log('[Frontend Debug] fetchLogs() - response.data.execution_duration_ms:', response.data?.execution_duration_ms);

      // 更新日志
      setCurrentLogs(response.data?.logs || []);
      console.log('[Frontend Debug] fetchLogs() - setCurrentLogs 完成');

      // 更新执行记录的持续时间（毫秒）
      if (response.data?.execution_duration_ms !== undefined) {
        setCurrentExecution(prev => ({
          ...prev,
          execution_duration_ms: response.data.execution_duration_ms
        }));
      }
    } catch (error) {
      console.error('[Frontend Debug] fetchLogs() - 获取日志失败:', error);
    }
  };

  const showLogs = async (record) => {
    setCurrentExecution(record);
    setLogModalVisible(true);
    fetchLogs(record.id);

    // 如果是运行中状态，开始轮询
    if (record.status === 'running' || record.status === 'pending') {
      startPollingLogs(record.id);
    }
  };

  const columns = [
    {
      title: '测试名称',
      key: 'name',
      render: (_, record) => {
        if (record.test_type === 'api' && record.api_request) {
          return <div>{record.api_request_name}</div>;
        }
        if (record.testcase) {
          return <div>{record.testcase_title}</div>;
        }
        return <div>未知测试</div>;
      }
    },
    {
      title: '类型',
      dataIndex: 'test_type',
      key: 'test_type',
      render: (text) => getTestTypeTag(text),
    },
    { title: '执行人', dataIndex: 'executor_name', key: 'executor_name', render: (name) => name || '未知' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag,
    },
    { title: '执行时间', dataIndex: 'executed_at', key: 'executed_at', render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        const menu = (
          <Menu onClick={({ key }) => handleStatusChange(record.id, key)}>
            <Menu.Item key="passed">标记为通过</Menu.Item>
            <Menu.Item key="failed">标记为失败</Menu.Item>
            <Menu.Item key="blocked">标记为阻塞</Menu.Item>
            <Menu.Item key="skipped">标记为跳过</Menu.Item>
          </Menu>
        );
        return (
          <Space>
            {/* 执行按钮 - 仅对API测试显示 */}
            {record.test_type === 'api' && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                size="small"
                onClick={() => handleExecuteApiTest(record)}
                loading={executingId === record.id}
                disabled={executingId === record.id}
              >
                执行
              </Button>
            )}

            {/* 查看日志按钮 */}
            <Button
              icon={<EyeOutlined />}
              size="small"
              onClick={() => showLogs(record)}
            >
              日志
            </Button>

            {/* 状态更新下拉菜单 */}
            <Dropdown overlay={menu}>
              <Button size="small" disabled={!hasCrudPermission()}>
                更新状态 <DownOutlined />
              </Button>
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试执行记录</Title>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3}>执行记录列表</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateExecution} disabled={!hasCrudPermission()}>
          新建执行
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={executions}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />

      {/* 创建执行记录模态框 */}
      <Modal
        title="新建执行记录"
        width={600}
        visible={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
        }}
        footer={null}
      >
        <Form form={createForm} layout="vertical" onFinish={handleSubmitCreate}>
          <Form.Item name="test_type" label="测试类型" rules={[{ required: true }]}>
            <Select placeholder="选择测试类型">
              <Option value="testcase" disabled>功能测试（开发中）</Option>
              <Option value="api">API测试</Option>
            </Select>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prevValues, curValues) => prevValues.test_type !== curValues.test_type}>
            {({ getFieldValue }) => {
              const render = getFieldValue('test_type') === 'testcase'
              console.log('[Frontend Debug] 渲染测试用例下拉框:', {
                test_type: getFieldValue('test_type'),
                shouldRender: render,
                testcaseListLength: testcaseList.length
              });
              return render ? (
                <Form.Item
                  name="testcase_id"
                  label="测试用例"
                  rules={[{ required: true, message: '请选择测试用例' }]}
                >
                  <Select placeholder="选择测试用例">
                    {testcaseList.map(tc => {
                      console.log('[Frontend Debug] 渲染测试用例选项:', tc.id, tc.title);
                      return <Option key={tc.id} value={tc.id}>{tc.title}</Option>;
                    })}
                  </Select>
                </Form.Item>
              ) : null
            }}
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prevValues, curValues) => prevValues.test_type !== curValues.test_type}>
            {({ getFieldValue }) => {
              const render = getFieldValue('test_type') === 'api'
              console.log('[Frontend Debug] 渲染API请求下拉框:', {
                test_type: getFieldValue('test_type'),
                shouldRender: render,
                apiRequestListLength: apiRequestList.length
              });
              return render ? (
                <Form.Item
                  name="api_request_id"
                  label="API请求"
                  rules={[{ required: true, message: '请选择API请求' }]}
                >
                  <Select placeholder="选择API请求">
                    {apiRequestList.map(api => {
                      console.log('[Frontend Debug] 渲染API请求选项:', api.id, api.name);
                      return <Option key={api.id} value={api.id}>{api.name}</Option>;
                    })}
                  </Select>
                </Form.Item>
              ) : null
            }}
          </Form.Item>

          <Form.Item name="comments" label="备注">
            <Input.TextArea rows={3} placeholder="输入备注信息（可选）" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" disabled={!hasCrudPermission()}>
              保存
            </Button>
            <Button
              style={{ marginLeft: 8 }}
              onClick={() => {
                setCreateModalVisible(false);
                createForm.resetFields();
              }}
            >
              取消
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 日志查看模态框 */}
      <Modal
        title={`执行日志 - ${currentExecution ? (currentExecution.api_request_name || currentExecution.testcase_title) : ''}`}
        width={800}
        visible={logModalVisible}
        onCancel={() => {
          setLogModalVisible(false);
          if (pollingInterval) {
            clearInterval(pollingInterval);
            setPollingInterval(null);
          }
        }}
        footer={[
          <Button key="close" onClick={() => setLogModalVisible(false)}>
            关闭
          </Button>
        ]}
      >
        <Card title="执行状态" size="small" style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="状态">
              {currentExecution ? getStatusTag(currentExecution.status) : null}
            </Descriptions.Item>
            <Descriptions.Item label="实际结果">
              {currentExecution?.actual_result || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="执行时间">
              {currentExecution?.executed_at ? new Date(currentExecution.executed_at).toLocaleString() : '-'}
            </Descriptions.Item>
            {currentExecution?.execution_duration_ms !== undefined && currentExecution?.execution_duration_ms !== null ? (
              <Descriptions.Item label="耗时">
                {currentExecution.execution_duration_ms.toFixed(2)}ms
              </Descriptions.Item>
            ) : null}
          </Descriptions>
        </Card>

        <Card title="实时日志" size="small">
          <div style={{
            background: '#f0f2f5',
            padding: 16,
            borderRadius: 4,
            maxHeight: 400,
            overflow: 'auto',
            fontFamily: 'monospace',
            fontSize: 12,
            lineHeight: 1.5
          }}>
            {currentLogs.length === 0 ? (
              <div style={{ color: '#999' }}>暂无日志...</div>
            ) : (
              currentLogs.map((log, index) => (
                <div key={index} style={{ marginBottom: 4 }}>
                  {log.split('\n').map((line, idx) => (
                    <div key={idx} style={{ color: line.includes('失败') ? '#ff4d4f' : line.includes('通过') ? '#52c41a' : '#333' }}>
                      {line}
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </Card>
      </Modal>
    </Space>
  );
}

export default TestExecutionList;