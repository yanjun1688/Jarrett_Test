import React, { useState, useEffect, useCallback } from 'react';
import {
  Button, Input, InputNumber, Select, Card, Space, Typography,
  Alert, message, Tag, Table, Tooltip, Empty,
  Statistic, Row, Col, Form, Descriptions, Modal, Breadcrumb, Switch,
  Radio, Divider, Popconfirm,
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined,
  ReloadOutlined, PlusOutlined,
  CheckCircleOutlined,
  SyncOutlined, CloudServerOutlined,
  HistoryOutlined, ProjectOutlined, HomeOutlined,
  DeleteOutlined, EditOutlined,
} from '@ant-design/icons';
import { advancedPressureTestAPI } from '../api/advancedPressureTest';
import { apiRequestsAPI } from '../api/apiRequests';
import { projectsAPI } from '../api/projects';
import { useAdvancedPressureTestWebSocket } from '../hooks/useAdvancedPressureTestWebSocket';
import ExecutionLogModal from './ExecutionLogModal';

const { Text, Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const EXTRACTOR_TYPES = [
  { value: 'json_path', label: 'JSON Path' },
  { value: 'regex', label: '正则表达式' },
  { value: 'header', label: '响应头' },
  { value: 'status_code', label: '状态码' },
  { value: 'xpath', label: 'XPath' },
];

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

const AdvancedPressureTestManager = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [apiRequests, setApiRequests] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [formVisible, setFormVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [execModalVisible, setExecModalVisible] = useState(false);
  const [execModalData, setExecModalData] = useState(null);
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [logModalContent, setLogModalContent] = useState('');
  const [stepModes, setStepModes] = useState({});

  const getToken = () => localStorage.getItem('authToken');
  const wsState = useAdvancedPressureTestWebSocket(getToken);

  const loadProjects = useCallback(async () => {
    try {
      const response = await projectsAPI.getAll();
      const projectList = response.data?.results || response.data?.data?.results || response.data || [];
      setProjects(Array.isArray(projectList) ? projectList : []);
    } catch (error) {
      message.error('加载项目列表失败: ' + (error.response?.data?.error || error.message));
    }
  }, []);

  const loadApiRequests = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const response = await apiRequestsAPI.getAll({ project: selectedProjectId });
      const data = response.data?.results || response.data?.data?.results || response.data || [];
      setApiRequests(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error('加载API请求失败: ' + (error.response?.data?.error || error.message));
    }
  }, [selectedProjectId]);

  const loadConfigs = useCallback(async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    try {
      const response = await advancedPressureTestAPI.config.getAll({ project: selectedProjectId });
      const configList = response.data?.results || response.data?.data?.results || response.data || [];
      setConfigs(Array.isArray(configList) ? configList : []);
    } catch (error) {
      message.error('加载配置失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (selectedProjectId) {
      loadApiRequests();
      loadConfigs();
    }
  }, [selectedProjectId, loadApiRequests, loadConfigs]);

  const scenarioFromForm = (values) => {
    const steps = (values.steps || []).map((step) => {
      const s = {
        name: step.name,
        weight: step.weight || 1,
      };
      if (step.mode === 'api_ref') {
        s.api_request_id = step.api_request_id;
      } else {
        s.url = step.url;
        s.method = step.method || 'GET';
        if (step.body) s.body = step.body;
      }
      if (step.headers) {
        try {
          s.headers = JSON.parse(step.headers);
        } catch {
          s.headers = {};
        }
      }
      if (step.think_time_enabled) {
        s.think_time = { min: step.think_time_min || 1, max: step.think_time_max || 3 };
      }
      if (step.extractors && step.extractors.length > 0) {
        s.extractors = step.extractors.filter((e) => e.name && e.type && e.expression);
      }
      return s;
    });

    return {
      scenario_name: values.scenario_name || '默认场景',
      think_time: {
        min: values.think_time_min || 1,
        max: values.think_time_max || 3,
      },
      steps,
    };
  };

  const handleSubmit = async (values) => {
    const data = {
      project: selectedProjectId,
      name: values.name,
      description: values.description || '',
      host: values.host,
      user_count: values.user_count,
      spawn_rate: values.spawn_rate,
      duration_seconds: values.duration_seconds,
      use_distributed: values.use_distributed || false,
      worker_count: values.use_distributed ? values.worker_count : 1,
      enable_web_ui: values.enable_web_ui !== false,
      web_ui_port: values.web_ui_port || 18089,
      scenario: scenarioFromForm(values),
    };

    try {
      let response;
      if (editingConfig) {
        response = await advancedPressureTestAPI.config.update(editingConfig.id, data);
      } else {
        response = await advancedPressureTestAPI.config.create(data);
      }
      if (response.status === 200 || response.status === 201 || response.data?.id) {
        message.success(editingConfig ? '配置更新成功' : '配置创建成功');
        setFormVisible(false);
        setEditingConfig(null);
        form.resetFields();
        await loadConfigs();
      }
    } catch (error) {
      const resp = error.response?.data;
      const errorMsg = resp
        ? typeof resp === 'string' ? resp : JSON.stringify(resp)
        : error.message;
      message.error((editingConfig ? '更新' : '创建') + '失败: ' + errorMsg);
    }
  };

  const openCreateForm = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      user_count: 100,
      spawn_rate: 10,
      duration_seconds: 60,
      use_distributed: false,
      worker_count: 1,
      enable_web_ui: true,
      web_ui_port: 18089,
      scenario_name: '',
      think_time_min: 1,
      think_time_max: 3,
    });
    setStepModes({});
    setFormVisible(true);
  };

  const openEditForm = (config) => {
    setEditingConfig(config);
    const sc = config.scenario || {};

    const modes = {};
    const steps = (sc.steps || []).map((step, idx) => {
      const hasApiRef = !!step.api_request_id;
      modes[idx] = hasApiRef ? 'api_ref' : 'direct';
      return {
        name: step.name,
        mode: hasApiRef ? 'api_ref' : 'direct',
        api_request_id: step.api_request_id || undefined,
        url: step.url || '',
        method: step.method || 'GET',
        body: step.body || '',
        weight: step.weight || 1,
        headers: step.headers ? JSON.stringify(step.headers, null, 2) : '',
        think_time_enabled: !!step.think_time,
        think_time_min: step.think_time?.min || 1,
        think_time_max: step.think_time?.max || 3,
        extractors: (step.extractors || []).map((e) => ({
          name: e.name || '',
          type: e.type || 'json_path',
          expression: e.expression || '',
        })),
      };
    });
    setStepModes(modes);

    form.setFieldsValue({
      name: config.name,
      description: config.description || '',
      host: config.host,
      user_count: config.user_count,
      spawn_rate: config.spawn_rate,
      duration_seconds: config.duration_seconds,
      use_distributed: config.use_distributed || false,
      worker_count: config.worker_count || 1,
      enable_web_ui: config.enable_web_ui !== false,
      web_ui_port: config.web_ui_port || 18089,
      scenario_name: sc.scenario_name || '',
      think_time_min: sc.think_time?.min || 1,
      think_time_max: sc.think_time?.max || 3,
      steps,
    });
    setFormVisible(true);
  };

  const handleViewHistory = async (config) => {
    setSelectedConfig(config);
    setHistoryVisible(true);
    try {
      const response = await advancedPressureTestAPI.config.getHistory(config.id);
      const data = response.data?.data || response.data || [];
      setExecutions(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error('加载历史失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleViewDetail = async (executionId) => {
    try {
      const response = await advancedPressureTestAPI.execution.getById(executionId);
      const detail = response.data?.data || response.data;
      setExecModalData({
        executionType: 'api',
        status: detail?.status === 'completed' ? 'success' : detail?.status === 'failed' ? 'error' : detail?.status,
        totalCount: detail?.total_requests || 0,
        passedCount: detail?.success_count || 0,
        failedCount: detail?.failed_count || 0,
        executionDuration: detail?.duration_seconds || 0,
        logs: detail?.logs || '暂无执行日志',
        errorMessage: detail?.error_log,
        startTime: detail?.started_at,
        endTime: detail?.finished_at,
      });
      setExecModalVisible(true);
    } catch (error) {
      message.error('加载详情失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleViewLogs = async (executionId) => {
    try {
      const response = await advancedPressureTestAPI.execution.getById(executionId);
      const detail = response.data?.data || response.data;
      setLogModalContent(detail?.logs || detail?.error_log || '暂无执行日志');
      setLogModalVisible(true);
    } catch (error) {
      message.error('加载日志失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleExecute = async (config) => {
    setSelectedConfig(config);
    wsState.reset();

    try {
      const response = await advancedPressureTestAPI.config.execute(config.id);
      if (response.data?.execution_id || response.data?.data?.execution_id) {
        const execId = response.data?.execution_id || response.data?.data?.execution_id;

        message.info('正在启动高级压测...');
        wsState.connect(execId);
      }
    } catch (error) {
      message.error('执行失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleDeleteConfig = async (config) => {
    try {
      await advancedPressureTestAPI.config.delete(config.id);
      message.success('配置已删除');
      await loadConfigs();
    } catch (error) {
      message.error('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleStart = () => {
    if (wsState.connected && wsState.authenticated) {
      wsState.startTest();
      message.info('高级压测已开始');
    } else {
      message.warning('WebSocket未连接或未认证');
    }
  };

  const handleStop = () => {
    wsState.stopTest();
  };

  const configColumns = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (val) => `${val}用户`,
    },
    {
      title: '启动速率',
      dataIndex: 'spawn_rate',
      key: 'spawn_rate',
      render: (val) => `${val}/s`,
    },
    {
      title: '持续时间',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (val) => `${val}秒`,
    },
    {
      title: '分布式',
      dataIndex: 'use_distributed',
      key: 'use_distributed',
      render: (val) => (val ? <Tag color="blue">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '场景步骤',
      key: 'steps_count',
      render: (_, record) => {
        const steps = record.scenario?.steps || [];
        return <Text type="secondary">{steps.length} 步</Text>;
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_, record) => (
        <Space>
          <Tooltip title="执行压测">
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleExecute(record)}
              size="small"
              disabled={wsState.running}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              icon={<EditOutlined />}
              onClick={() => openEditForm(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="历史记录">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record)}
              size="small"
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此配置？"
            onConfirm={() => handleDeleteConfig(record)}
            okText="删除"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><HomeOutlined /> 首页</Breadcrumb.Item>
        <Breadcrumb.Item><CloudServerOutlined /> 高级压测</Breadcrumb.Item>
      </Breadcrumb>

      <Title level={2} style={{ marginBottom: 24 }}>
        <CloudServerOutlined style={{ color: '#1890ff', marginRight: 8 }} />
        高级压测 (Locust)
      </Title>

      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Card>
          <Space>
            <ProjectOutlined />
            <Text strong>选择项目：</Text>
            <Select
              value={selectedProjectId}
              onChange={(value) => {
                setSelectedProjectId(value);
                setSelectedConfig(null);
                wsState.reset();
              }}
              placeholder="请选择项目"
              style={{ width: 200 }}
              showSearch
              optionFilterProp="children"
            >
              {projects.map((p) => (
                <Option key={p.id} value={p.id}>{p.name}</Option>
              ))}
            </Select>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadConfigs}
              loading={loading}
              disabled={!selectedProjectId}
            >
              刷新配置列表
            </Button>
          </Space>
        </Card>

        {selectedConfig && (
          <Card
            title="执行监控"
          >
            {!wsState.running && !wsState.summary && wsState.connected && (
              <>
                <Alert
                  type="success"
                  message={<Space><CheckCircleOutlined /> 已连接，准备就绪</Space>}
                  description={`配置: ${selectedConfig.name} | 目标: ${selectedConfig.host}`}
                  style={{ marginBottom: 16 }}
                />
                <Button
                  type="primary" size="large"
                  icon={<PlayCircleOutlined />}
                  onClick={handleStart} block
                >
                  开始压测
                </Button>
              </>
            )}

            {wsState.running && (
              <>
                <Alert
                  type="info"
                  message={<Space><SyncOutlined spin /> 正在执行 ({selectedConfig.duration_seconds}秒)</Space>}
                  style={{ marginBottom: 16 }}
                />
                <Row gutter={16}>
                  <Col span={4}>
                    <Statistic title="当前用户" value={wsState.stats?.current_users || 0} suffix={`/ ${selectedConfig.user_count}`} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="总请求" value={wsState.stats?.total_requests || 0} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="RPS" value={wsState.stats?.rps?.toFixed(2) || wsState.stats?.throughput?.toFixed(2) || 0} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="成功率" value={100 - (wsState.stats?.fail_ratio || wsState.stats?.error_rate || 0)} suffix="%" />
                  </Col>
                  <Col span={4}>
                    <Statistic title="平均响应" value={wsState.stats?.avg_response_time?.toFixed(2) || 0} suffix="ms" />
                  </Col>
                  <Col span={4}>
                    <Button type="primary" danger icon={<PauseCircleOutlined />} onClick={handleStop} block>
                      停止
                    </Button>
                  </Col>
                </Row>
              </>
            )}

            {wsState.summary && (
              <Card
                title={<Space><CheckCircleOutlined style={{ color: '#52c41a' }} />压测完成</Space>}
                style={{ borderColor: '#52c41a', marginTop: 16 }}
              >
                <Descriptions bordered column={4} size="small">
                  <Descriptions.Item label="总请求数">{wsState.summary.total_requests}</Descriptions.Item>
                  <Descriptions.Item label="成功数">{wsState.summary.success_count}</Descriptions.Item>
                  <Descriptions.Item label="失败数">{wsState.summary.failed_count}</Descriptions.Item>
                  <Descriptions.Item label="错误率">{wsState.summary.error_rate?.toFixed(2)}%</Descriptions.Item>
                  <Descriptions.Item label="平均响应">{wsState.summary.avg_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="最小响应">{wsState.summary.min_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="最大响应">{wsState.summary.max_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="吞吐量">{wsState.summary.throughput?.toFixed(2)} RPS</Descriptions.Item>
                  <Descriptions.Item label="P50">{wsState.summary.p50_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="P90">{wsState.summary.p90_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="P95">{wsState.summary.p95_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="P99">{wsState.summary.p99_response_time?.toFixed(2)}ms</Descriptions.Item>
                  <Descriptions.Item label="峰值用户">{wsState.summary.peak_users}</Descriptions.Item>
                  <Descriptions.Item label="持续时间">{wsState.summary.duration_seconds}秒</Descriptions.Item>
                </Descriptions>

                {wsState.summary.requests_per_endpoint && Object.keys(wsState.summary.requests_per_endpoint).length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <Text strong>端点统计：</Text>
                    <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                      {Object.entries(wsState.summary.requests_per_endpoint).map(([name, data]) => (
                        <Col span={6} key={name}>
                          <Card size="small">
                            <Statistic title={name} value={data.requests} suffix={`请求 | ${data.failures}失败`} />
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </div>
                )}

                <Button
                  type="primary" style={{ marginTop: 16 }}
                  onClick={() => {
                    setSelectedConfig(null);
                    wsState.reset();
                  }}
                >
                  返回配置列表
                </Button>
              </Card>
            )}

            {wsState.error && (
              <Alert type="error" message="执行出错" description={wsState.error} style={{ marginTop: 16 }} />
            )}
          </Card>
        )}

        <Card
          title="压测配置"
          extra={
            <Button
              type="primary" icon={<PlusOutlined />}
              onClick={openCreateForm}
              disabled={!selectedProjectId || wsState.running}
            >
              新建配置
            </Button>
          }
        >
          <Table
            columns={configColumns}
            dataSource={configs}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            size="small"
            locale={{
              emptyText: (
                <Empty
                  description={
                    !selectedProjectId
                      ? '请先选择项目'
                      : '暂无配置，点击「新建配置」创建'
                  }
                />
              ),
            }}
          />
        </Card>
      </Space>

      {/* ── 新建/编辑配置 Modal ── */}
      <Modal
        title={editingConfig ? '编辑高级压测配置' : '新建高级压测配置'}
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          setEditingConfig(null);
          form.resetFields();
        }}
        footer={null}
        width={900}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Card title="基础配置" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="name" label="配置名称" rules={[{ required: true, message: '请输入配置名称' }]}>
                  <Input placeholder="例如：登录-浏览-下单压测" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="description" label="配置描述">
                  <Input placeholder="可选描述" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="host" label="目标地址" rules={[{ required: true, message: '请输入目标地址' }]}>
              <Input placeholder="http://localhost:8080" />
            </Form.Item>
          </Card>

          <Card title="Locust 参数" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="user_count" label="并发用户数" rules={[{ required: true }]}>
                  <InputNumber min={1} max={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="spawn_rate" label="启动速率(用户/秒)" rules={[{ required: true }]}>
                  <InputNumber min={1} max={500} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="duration_seconds" label="持续时间(秒)" rules={[{ required: true }]}>
                  <InputNumber min={1} max={3600} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="use_distributed" valuePropName="checked" label="启用分布式">
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="worker_count" label="Worker 数量">
                  <InputNumber min={1} max={20} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
          <Form.Item name="web_ui_port" label="Web UI 端口" hidden>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="enable_web_ui" valuePropName="checked" hidden>
            <Switch defaultChecked />
          </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="web_ui_port" label="Web UI 端口">
                  <InputNumber min={1024} max={65535} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card title="场景编排" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="scenario_name" label="场景名称">
                  <Input placeholder="例如：用户购物流程" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="think_time_min" label="全局等待时间(最小秒)">
                  <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="think_time_max" label="全局等待时间(最大秒)">
                  <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Divider>步骤列表</Divider>
            <Form.List name="steps">
              {(fields, { add, remove }) => (
                <>
                  {fields.length === 0 && (
                    <Alert
                      type="warning"
                      message="尚未添加任何步骤，请点击下方按钮添加"
                      style={{ marginBottom: 12 }}
                    />
                  )}
                  {fields.map(({ key, name, ...rest }, idx) => (
                    <Card
                      key={key}
                      size="small"
                      title={`步骤 ${idx + 1}`}
                      style={{ marginBottom: 12, borderLeft: '3px solid #1890ff' }}
                      extra={
                        <Button
                          type="text" danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                        >
                          删除
                        </Button>
                      }
                    >
                      <Row gutter={16}>
                        <Col span={10}>
                          <Form.Item
                            {...rest}
                            name={[name, 'name']}
                            label="步骤名称"
                            rules={[{ required: true, message: '必填' }]}
                          >
                            <Input placeholder="例如：登录" />
                          </Form.Item>
                        </Col>
                        <Col span={4}>
                          <Form.Item
                            {...rest}
                            name={[name, 'weight']}
                            label="权重"
                            rules={[{ required: true, message: '必填' }]}
                          >
                            <InputNumber min={1} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col span={10}>
                          <Form.Item
                            {...rest}
                            name={[name, 'mode']}
                            label="请求定义方式"
                            initialValue="api_ref"
                          >
                            <Radio.Group
                              onChange={(e) => {
                                setStepModes((prev) => ({ ...prev, [idx]: e.target.value }));
                              }}
                            >
                              <Radio value="api_ref">引用已有 API</Radio>
                              <Radio value="direct">直接定义</Radio>
                            </Radio.Group>
                          </Form.Item>
                        </Col>
                      </Row>

                      {(stepModes[idx] || 'api_ref') === 'api_ref' ? (
                        <Form.Item
                          {...rest}
                          name={[name, 'api_request_id']}
                          label="选择 API 请求"
                          rules={[{ required: true, message: '请选择 API 请求' }]}
                        >
                          <Select
                            placeholder="选择 API 请求"
                            showSearch
                            optionFilterProp="children"
                            notFoundContent={
                              apiRequests.length === 0
                                ? '当前项目无 API 请求，请先创建'
                                : undefined
                            }
                          >
                            {apiRequests.map((api) => (
                              <Option key={api.id} value={api.id}>
                                {api.name} - {api.method} {api.url}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      ) : (
                        <Row gutter={16}>
                          <Col span={6}>
                            <Form.Item
                              {...rest}
                              name={[name, 'method']}
                              label="HTTP 方法"
                              rules={[{ required: true }]}
                              initialValue="GET"
                            >
                              <Select>
                                {HTTP_METHODS.map((m) => (
                                  <Option key={m} value={m}>{m}</Option>
                                ))}
                              </Select>
                            </Form.Item>
                          </Col>
                          <Col span={18}>
                            <Form.Item
                              {...rest}
                              name={[name, 'url']}
                              label="URL 路径"
                              rules={[{ required: true, message: '必填' }]}
                            >
                              <Input placeholder="/api/login" />
                            </Form.Item>
                          </Col>
                        </Row>
                      )}

                      <Form.Item
                        {...rest}
                        name={[name, 'body']}
                        label="请求体 (JSON)"
                      >
                        <TextArea rows={2} placeholder='{"user": "test"}' />
                      </Form.Item>

                      <Form.Item
                        {...rest}
                        name={[name, 'headers']}
                        label="自定义 Headers (JSON)"
                      >
                        <TextArea
                          rows={2}
                          placeholder='{"Content-Type": "application/json"}'
                        />
                      </Form.Item>

                      <Row gutter={16}>
                        <Col span={8}>
                          <Form.Item
                            {...rest}
                            name={[name, 'think_time_enabled']}
                            valuePropName="checked"
                          >
                            <Switch checkedChildren="自定义等待" unCheckedChildren="全局等待" />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item
                            {...rest}
                            name={[name, 'think_time_min']}
                            label="最小秒"
                          >
                            <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item
                            {...rest}
                            name={[name, 'think_time_max']}
                            label="最大秒"
                          >
                            <InputNumber min={0} step={0.5} style={{ width: '100%' }} />
                          </Form.Item>
                        </Col>
                      </Row>

                      <Divider>数据提取器（可选，步骤间变量传递）</Divider>
                      <Form.List name={[name, 'extractors']}>
                        {(extFields, { add: addExt, remove: removeExt }) => (
                          <>
                            {extFields.map(({ key: extKey, name: extName, ...extRest }, extIdx) => (
                              <Row key={extKey} gutter={8} align="middle" style={{ marginBottom: 8 }}>
                                <Col span={5}>
                                  <Form.Item
                                    {...extRest}
                                    name={[extName, 'name']}
                                    rules={[{ required: true, message: '必填' }]}
                                    noStyle
                                  >
                                    <Input placeholder="变量名" />
                                  </Form.Item>
                                </Col>
                                <Col span={5}>
                                  <Form.Item
                                    {...extRest}
                                    name={[extName, 'type']}
                                    rules={[{ required: true }]}
                                    noStyle
                                    initialValue="json_path"
                                  >
                                    <Select>
                                      {EXTRACTOR_TYPES.map((t) => (
                                        <Option key={t.value} value={t.value}>{t.label}</Option>
                                      ))}
                                    </Select>
                                  </Form.Item>
                                </Col>
                                <Col span={12}>
                                  <Form.Item
                                    {...extRest}
                                    name={[extName, 'expression']}
                                    rules={[{ required: true, message: '必填' }]}
                                    noStyle
                                  >
                                    <Input placeholder="$.data.token 或 (\\w+)@test.com" />
                                  </Form.Item>
                                </Col>
                                <Col span={2}>
                                  <Button
                                    type="text" danger
                                    icon={<DeleteOutlined />}
                                    onClick={() => removeExt(extName)}
                                  />
                                </Col>
                              </Row>
                            ))}
                            <Button
                              type="dashed"
                              icon={<PlusOutlined />}
                              onClick={() => addExt({ type: 'json_path' })}
                              block
                              size="small"
                            >
                              添加提取器
                            </Button>
                          </>
                        )}
                      </Form.List>
                    </Card>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => {
                      const newIdx = fields.length;
                      add({ mode: 'api_ref', weight: 1, method: 'GET' });
                      setStepModes((prev) => ({ ...prev, [newIdx]: 'api_ref' }));
                    }}
                    block
                    icon={<PlusOutlined />}
                    style={{ marginTop: 8 }}
                  >
                    添加步骤
                  </Button>
                </>
              )}
            </Form.List>
          </Card>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingConfig ? '保存修改' : '创建配置'}
              </Button>
              <Button onClick={() => {
                setFormVisible(false);
                setEditingConfig(null);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 历史记录 Modal */}
      <Modal
        title="执行历史记录"
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={null}
        width={800}
      >
        <Table
          dataSource={executions}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: 'ID', dataIndex: 'id', key: 'id' },
            {
              title: '状态', dataIndex: 'status', key: 'status',
              render: (s) => <Tag color={s === 'completed' ? 'green' : 'blue'}>{s}</Tag>,
            },
            { title: '总请求', dataIndex: 'total_requests', key: 'total_requests' },
            {
              title: '成功率', key: 'success_rate',
              render: (_, r) =>
                r.total_requests > 0
                  ? `${((r.success_count / r.total_requests) * 100).toFixed(1)}%`
                  : '0%',
            },
            { title: '开始时间', dataIndex: 'started_at', key: 'started_at' },
            {
              title: '操作', key: 'action',
              render: (_, r) => (
                <Space size="small">
                  <Button size="small" type="primary" ghost onClick={() => handleViewDetail(r.id)}>详情</Button>
                  <Button size="small" onClick={() => handleViewLogs(r.id)}>日志</Button>
                </Space>
              ),
            },
          ]}
          locale={{ emptyText: '暂无执行记录' }}
        />
      </Modal>

      {/* 执行日志 - 纯文本 */}
      <Modal
        title="执行日志"
        open={logModalVisible}
        onCancel={() => setLogModalVisible(false)}
        footer={[<Button key="close" onClick={() => setLogModalVisible(false)}>关闭</Button>]}
        width={900}
      >
        <Card style={{ background: '#0d1117', maxHeight: 550, overflow: 'auto' }}>
          <pre style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap', color: '#c9d1d9', lineHeight: 1.6 }}>
            {logModalContent}
          </pre>
        </Card>
      </Modal>

      {/* 执行详情 - 结构化报表 */}
      <ExecutionLogModal
        visible={execModalVisible}
        onClose={() => setExecModalVisible(false)}
        title="高级压测执行日志"
        executionType="api"
        status={execModalData?.status || 'pending'}
        totalCount={execModalData?.totalCount || 0}
        passedCount={execModalData?.passedCount || 0}
        failedCount={execModalData?.failedCount || 0}
        executionDuration={execModalData?.executionDuration || 0}
        logs={execModalData?.logs || ''}
        errorMessage={execModalData?.errorMessage}
        startTime={execModalData?.startTime}
        endTime={execModalData?.endTime}
      />
    </div>
  );
};

export default AdvancedPressureTestManager;
