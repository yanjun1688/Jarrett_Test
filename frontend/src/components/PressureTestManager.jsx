/**
 * 压测管理页面组件
 * 提供压测配置管理、执行监控、历史查看功能
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Button,
  Input,
  InputNumber,
  Select,
  Card,
  Space,
  Typography,
  Alert,
  message,
  Tag,
  Popconfirm,
  Drawer,
  Table,
  Tooltip,
  Empty,
  Progress,
  Statistic,
  Row,
  Col,
  Form,
  Descriptions,
  Modal,
  Breadcrumb
} from 'antd';
import {
  ThunderboltOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  PlusOutlined,
  EditOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DashboardOutlined,
  RocketOutlined,
  HistoryOutlined,
  ProjectOutlined,
  HomeOutlined
} from '@ant-design/icons';
import { pressureTestAPI } from '../api/pressureTest';
import { apiRequestsAPI } from '../api/apiRequests';
import { projectsAPI } from '../api/projects';
import { usePressureTestWebSocket } from '../hooks/usePressureTestWebSocket';
import ResponseTimeChart from './ResponseTimeChart';
import moment from 'moment';

const { Text, Title } = Typography;
const { Option } = Select;

const PRESSURE_MODES = {
  instant: {
    label: '瞬时并发',
    description: '同时发起N个请求',
    icon: <ThunderboltOutlined />,
    color: '#1890ff'
  },
  sustained: {
    label: '持续并发',
    description: '每秒X个，持续Y秒',
    icon: <RocketOutlined />,
    color: '#52c41a'
  },
  batch: {
    label: '分批并发',
    description: '每批N个，间隔T秒',
    icon: <DashboardOutlined />,
    color: '#722ed1'
  }
};

const renderStatusTag = (status) => {
  const statusMap = {
    pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
    running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
    completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
    stopped: { color: 'warning', icon: <PauseCircleOutlined />, text: '已停止' },
    failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
  };
  const config = statusMap[status] || statusMap.pending;
  return (
    <Tag icon={config.icon} color={config.color}>
      {config.text}
    </Tag>
  );
};

const PressureTestConfigForm = ({ form, initialValues, apiRequests, onSubmit, onCancel }) => {
  const [pressureMode, setPressureMode] = useState(initialValues?.pressure_mode || 'instant');

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      onSubmit(values);
    } catch (err) {
      console.error('Form validation error:', err);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues || {
        pressure_mode: 'instant',
        request_count: 100,
        rate_per_second: 10,
        duration_seconds: 60,
        batch_size: 50,
        batch_interval: 5,
        max_concurrent: 100
      }}
    >
      <Form.Item
        name="name"
        label="配置名称"
        rules={[{ required: true, message: '请输入配置名称' }]}
      >
        <Input placeholder="例如：登录接口压测" />
      </Form.Item>

      <Form.Item
        name="api_request"
        label="测试API"
        rules={[{ required: true, message: '请选择测试API' }]}
        extra={apiRequests.length === 0 ? 
          <Alert type="warning" message="当前项目下没有API请求，请先前往「API测试」页面创建API请求" style={{ marginTop: 8 }} /> :
          `当前项目下有 ${apiRequests.length} 个API请求可选`
        }
      >
        <Select placeholder={apiRequests.length === 0 ? "暂无API请求可选" : "选择要压测的API请求"} showSearch optionFilterProp="children" disabled={apiRequests.length === 0}>
          {apiRequests.map(api => (
            <Option key={api.id} value={api.id}>
              {api.name} - {api.method} {api.url}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item
        name="pressure_mode"
        label="压测模式"
        rules={[{ required: true, message: '请选择压测模式' }]}
      >
        <Select onChange={setPressureMode}>
          {Object.entries(PRESSURE_MODES).map(([key, mode]) => (
            <Option key={key} value={key}>
              <Space>
                {mode.icon}
                <span style={{ color: mode.color }}>{mode.label}</span>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ({mode.description})
                </Text>
              </Space>
            </Option>
          ))}
        </Select>
      </Form.Item>

      {pressureMode === 'instant' && (
        <Form.Item
          name="request_count"
          label="总请求数"
          rules={[{ required: true, message: '请输入总请求数' }]}
          extra="瞬时并发模式下同时发起的总请求数（最大1000）"
        >
          <InputNumber min={1} max={1000} style={{ width: '100%' }} />
        </Form.Item>
      )}

      {pressureMode === 'sustained' && (
        <>
          <Form.Item
            name="rate_per_second"
            label="每秒请求数"
            rules={[{ required: true, message: '请输入每秒请求数' }]}
            extra="持续并发模式下每秒发起的请求数"
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="duration_seconds"
            label="持续秒数"
            rules={[{ required: true, message: '请输入持续秒数' }]}
            extra="压测持续的总秒数"
          >
            <InputNumber min={1} max={600} style={{ width: '100%' }} />
          </Form.Item>
        </>
      )}

      {pressureMode === 'batch' && (
        <>
          <Form.Item
            name="request_count"
            label="总请求数"
            rules={[{ required: true, message: '请输入总请求数' }]}
            extra="分批并发模式下的总请求数（最大1000）"
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="batch_size"
            label="每批数量"
            rules={[{ required: true, message: '请输入每批数量' }]}
            extra="每批发起的请求数"
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="batch_interval"
            label="批次间隔(秒)"
            rules={[{ required: true, message: '请输入批次间隔' }]}
            extra="批次之间的等待时间"
          >
            <InputNumber min={1} max={60} style={{ width: '100%' }} />
          </Form.Item>
        </>
      )}

      <Form.Item
        name="max_concurrent"
        label="最大并发数"
        extra="同时最多发起的请求数（最大1000）"
      >
        <InputNumber min={1} max={1000} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" onClick={handleSubmit}>
            {initialValues ? '更新配置' : '创建配置'}
          </Button>
          <Button onClick={onCancel}>取消</Button>
        </Space>
      </Form.Item>
    </Form>
  );
};

const ExecutionMonitor = ({ wsState, onStart, onStop, configName }) => {
  const { running, stats, summary, connected, authenticated } = wsState;

  if (!running && !summary) {
    if (connected && authenticated) {
      return (
        <Card style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Alert
              type="success"
              message={<Space><CheckCircleOutlined /> 已连接，准备就绪</Space>}
              description={`压测配置: ${configName}`}
            />
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={onStart}
              block
            >
              开始压测
            </Button>
            <Alert
              type="info"
              message="压测模式说明"
              description={
                <div>
                  <ul style={{ paddingLeft: 20, margin: 0 }}>
                    <li><ThunderboltOutlined style={{ color: '#1890ff' }} /> <strong>瞬时并发</strong>：同时发起N个请求</li>
                    <li><RocketOutlined style={{ color: '#52c41a' }} /> <strong>持续并发</strong>：每秒X个请求持续Y秒</li>
                    <li><DashboardOutlined style={{ color: '#722ed1' }} /> <strong>分批并发</strong>：每批N个请求间隔T秒</li>
                  </ul>
                </div>
              }
            />
          </Space>
        </Card>
      );
    }
    return (
      <Alert
        type="info"
        message="压测说明"
        description={
          <div>
            <p>压测功能支持三种模式：</p>
            <ul>
              <li><ThunderboltOutlined style={{ color: '#1890ff' }} /> <strong>瞬时并发</strong>：同时发起N个请求，测试瞬间负载能力</li>
              <li><RocketOutlined style={{ color: '#52c41a' }} /> <strong>持续并发</strong>：每秒X个请求持续Y秒，测试持续负载能力</li>
              <li><DashboardOutlined style={{ color: '#722ed1' }} /> <strong>分批并发</strong>：每批N个请求间隔T秒，测试阶梯负载能力</li>
            </ul>
            <p>选择项目后，创建压测配置并点击执行按钮开始压测。</p>
          </div>
        }
      />
    );
  }

  const percent = stats ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div>
      {running && (
        <>
          <Alert
            type="info"
            message={<Space><SyncOutlined spin /> 正在执行: {configName}</Space>}
            style={{ marginBottom: 16 }}
          />
          <Progress 
            percent={percent} 
            status="active"
            format={() => `${stats?.completed || 0} / ${stats?.total || 0}`}
          />
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={4}>
              <Statistic 
                title="RPS" 
                value={stats?.rps || 0} 
                suffix="req/s"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={4}>
              <Statistic 
                title="成功率" 
                value={stats?.successRate || 0} 
                suffix="%"
                valueStyle={{ color: stats?.successRate > 95 ? '#52c41a' : '#faad14' }}
              />
            </Col>
            <Col span={4}>
              <Statistic 
                title="平均响应" 
                value={stats?.avgResponseTime || 0} 
                suffix="ms"
                valueStyle={{ color: stats?.avgResponseTime < 200 ? '#52c41a' : '#faad14' }}
              />
            </Col>
            <Col span={4}>
              <Statistic 
                title="已完成" 
                value={stats?.completed || 0}
              />
            </Col>
            <Col span={4}>
              <Statistic 
                title="总请求" 
                value={stats?.total || 0}
              />
            </Col>
            <Col span={4}>
              <Button 
                type="primary" 
                danger 
                icon={<PauseCircleOutlined />}
                onClick={onStop}
                block
              >
                停止
              </Button>
            </Col>
          </Row>
        </>
      )}

      {summary && (
        <Card 
          title={<Space><CheckCircleOutlined style={{ color: '#52c41a' }} />压测完成</Space>}
          style={{ borderColor: '#52c41a', marginTop: 16 }}
        >
          <Descriptions bordered column={3} size="small">
            <Descriptions.Item label="总请求数">{summary.totalRequests}</Descriptions.Item>
            <Descriptions.Item label="成功数">{summary.successCount}</Descriptions.Item>
            <Descriptions.Item label="失败数">{summary.failedCount}</Descriptions.Item>
            <Descriptions.Item label="错误率">{summary.errorRate}%</Descriptions.Item>
            <Descriptions.Item label="平均响应">{summary.avgResponseTime}ms</Descriptions.Item>
            <Descriptions.Item label="吞吐量">{summary.throughput} RPS</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
};

const PressureTestManager = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [apiRequests, setApiRequests] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [formVisible, setFormVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [executionDetail, setExecutionDetail] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [rawResults, setRawResults] = useState([]);

  const getToken = () => localStorage.getItem('authToken');
  const wsState = usePressureTestWebSocket(getToken);

  const loadProjects = useCallback(async () => {
    try {
      const response = await projectsAPI.getAll();
      // DRF ViewSet 返回格式: {results: [...], count: ...}
      const projectList = response.data?.results || response.data?.data?.results || response.data || [];
      setProjects(Array.isArray(projectList) ? projectList : []);
      // 不自动选择项目，让用户自己选择
    } catch (error) {
      message.error('加载项目列表失败: ' + (error.response?.data?.error || error.message));
    }
  }, []);

  const loadConfigs = useCallback(async () => {
    if (!selectedProjectId) return;
    setLoading(true);
    try {
      console.log('[压测] 加载配置, projectId:', selectedProjectId);
      const response = await pressureTestAPI.config.getAll({ project: selectedProjectId });
      console.log('[压测] 配置列表响应:', response.status, response.data);
      // DRF ViewSet 返回格式: {results: [...], count: ...}
      const configList = response.data?.results || response.data?.data?.results || response.data || [];
      console.log('[压测] 解析后的配置列表:', configList);
      setConfigs(Array.isArray(configList) ? configList : []);
    } catch (error) {
      console.error('[压测] 加载配置失败:', error.response);
      message.error('加载配置失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  const loadApiRequests = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const response = await apiRequestsAPI.getAll({ project: selectedProjectId });
      // DRF ViewSet 返回格式: {results: [...], count: ...} 或分页格式
      const data = response.data?.results || response.data?.data?.results || response.data || [];
      setApiRequests(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Load API requests error:', error);
      message.warning('加载API请求列表失败，请确保项目下有已创建的API请求');
      setApiRequests([]);
    }
  }, [selectedProjectId]);

  const handleCreateConfig = async (values) => {
    try {
      const data = {
        ...values,
        project: selectedProjectId
      };
      console.log('[压测] 创建配置请求:', data);
      const response = await pressureTestAPI.config.create(data);
      console.log('[压测] 创建配置响应:', response.status, response.data);
      // DRF ViewSet create 返回 status 201 和创建的对象数据
      if (response.status === 201 || response.data?.id) {
        message.success('配置创建成功');
        setFormVisible(false);
        form.resetFields();
        await loadConfigs(); // 确保等待刷新完成
      } else {
        message.warning('创建响应异常，请检查列表');
        console.log('[压测] Create response:', response);
      }
    } catch (error) {
      console.error('[压测] 创建失败:', error.response);
      const errorMsg = error.response?.data?.error || 
                       Object.values(error.response?.data || {}).join(', ') ||
                       error.message;
      message.error('创建失败: ' + errorMsg);
    }
  };

  const handleUpdateConfig = async (values) => {
    try {
      const response = await pressureTestAPI.config.update(editingConfig.id, values);
      // DRF ViewSet update 返回 status 200 和更新的对象数据
      if (response.status === 200 || response.data?.id) {
        message.success('配置更新成功');
        setFormVisible(false);
        setEditingConfig(null);
        form.resetFields();
        await loadConfigs();
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       Object.values(error.response?.data || {}).join(', ') ||
                       error.message;
      message.error('更新失败: ' + errorMsg);
    }
  };

  const handleDeleteConfig = async (id) => {
    try {
      await pressureTestAPI.config.delete(id);
      message.success('删除成功');
      loadConfigs();
    } catch (error) {
      message.error('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleExecute = async (config) => {
    setSelectedConfig(config);
    wsState.reset();

    try {
      const response = await pressureTestAPI.config.execute(config.id);
      if (response.data?.execution_id || response.data?.data?.execution_id) {
        const execId = response.data?.execution_id || response.data?.data?.execution_id;
        message.info('正在启动压测...');
        wsState.connect(execId);
        message.info('WebSocket连接已建立，请点击"开始压测"按钮');
      }
    } catch (error) {
      message.error('执行失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleStart = () => {
    if (wsState.connected && wsState.authenticated) {
      wsState.startTest();
      message.info('压测已开始');
    } else {
      message.warning('WebSocket未连接或未认证');
    }
  };

  const handleStop = () => {
    wsState.stopTest();
  };

  const handleViewHistory = async (config) => {
    setSelectedConfig(config);
    setHistoryVisible(true);
    try {
      const response = await pressureTestAPI.config.getHistory(config.id);
      if (response.data) {
        setExecutions(response.data?.data || response.data || []);
      }
    } catch (error) {
      message.error('加载历史失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleViewDetail = async (execution) => {
    try {
      const response = await pressureTestAPI.execution.getById(execution.id);
      if (response.data) {
        const detail = response.data?.data || response.data;
        setExecutionDetail(detail);
        
        // 处理原始结果数据用于图表
        if (detail.raw_results && Array.isArray(detail.raw_results)) {
          setRawResults(detail.raw_results.map(r => ({
            index: r.index,
            responseTime: r.response_time_ms,
            success: r.success
          })));
        } else {
          setRawResults([]);
        }
        
        setDetailVisible(true);
      }
    } catch (error) {
      message.error('加载详情失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleEdit = (config) => {
    setEditingConfig(config);
    setFormVisible(true);
    form.setFieldsValue(config);
  };

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // 选择项目后只加载API请求列表，配置列表由用户手动刷新
  useEffect(() => {
    if (selectedProjectId) {
      loadApiRequests();
      // 清空配置列表，等用户手动刷新
      setConfigs([]);
    }
  }, [selectedProjectId, loadApiRequests]);

  const configColumns = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>
    },
    {
      title: 'API请求',
      dataIndex: 'api_request_name',
      key: 'api_request_name',
      render: (text) => text || '-'
    },
    {
      title: '压测模式',
      dataIndex: 'pressure_mode',
      key: 'pressure_mode',
      render: (mode) => {
        const config = PRESSURE_MODES[mode];
        return (
          <Tag color={config?.color} icon={config?.icon}>
            {config?.label || mode}
          </Tag>
        );
      }
    },
    {
      title: '参数',
      key: 'params',
      render: (_, record) => {
        if (record.pressure_mode === 'instant') {
          return `${record.request_count || 0}次`;
        } else if (record.pressure_mode === 'sustained') {
          return `${record.rate_per_second || 0}req/s × ${record.duration_seconds || 0}s`;
        } else if (record.pressure_mode === 'batch') {
          const batchCount = Math.ceil((record.request_count || 0) / (record.batch_size || 1));
          return `${record.batch_size || 0}个/批 × ${batchCount}批`;
        }
        return '-';
      }
    },
    {
      title: '最大并发',
      dataIndex: 'max_concurrent',
      key: 'max_concurrent',
      render: (val) => `${val || 100}`
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
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
              onClick={() => handleEdit(record)}
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
            title="确定删除此配置吗？"
            onConfirm={() => handleDeleteConfig(record.id)}
          >
            <Tooltip title="删除">
              <Button 
                danger 
                icon={<DeleteOutlined />}
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const historyColumns = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: renderStatusTag
    },
    {
      title: '总请求数',
      dataIndex: 'total_requests',
      key: 'total_requests'
    },
    {
      title: '成功数',
      dataIndex: 'success_count',
      key: 'success_count'
    },
    {
      title: '错误率',
      dataIndex: 'error_rate',
      key: 'error_rate',
      render: (rate) => rate ? `${rate}%` : '-'
    },
    {
      title: '平均响应',
      dataIndex: 'avg_response_time',
      key: 'avg_response_time',
      render: (time) => time ? `${time}ms` : '-'
    },
    {
      title: '执行时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (time) => time ? moment(time).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button 
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
          size="small"
        >
          详情
        </Button>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><HomeOutlined /> 首页</Breadcrumb.Item>
        <Breadcrumb.Item><ThunderboltOutlined /> 压测功能</Breadcrumb.Item>
      </Breadcrumb>

      <Title level={2} style={{ marginBottom: 24 }}>
        <ThunderboltOutlined style={{ color: '#1890ff', marginRight: 8 }} />
        压测功能
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
              {projects.map(p => (
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

        <Card title="执行监控">
          <ExecutionMonitor 
            wsState={wsState} 
            onStart={handleStart}
            onStop={handleStop} 
            configName={selectedConfig?.name}
          />
        </Card>

        <Card 
          title="压测配置"
          extra={
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingConfig(null);
                setFormVisible(true);
              }}
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
            locale={{ emptyText: 
              <Empty 
                description={
                  !selectedProjectId 
                    ? "请先选择项目" 
                    : configs.length === 0 && !loading 
                      ? "点击「刷新配置列表」查看已有配置，或点击「新建配置」创建新配置" 
                      : "加载中..."
                } 
              /> 
            }}
          />
        </Card>
      </Space>

      <Modal
        title={editingConfig ? '编辑压测配置' : '新建压测配置'}
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          setEditingConfig(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <PressureTestConfigForm
          form={form}
          initialValues={editingConfig}
          apiRequests={apiRequests}
          onSubmit={editingConfig ? handleUpdateConfig : handleCreateConfig}
          onCancel={() => {
            setFormVisible(false);
            setEditingConfig(null);
            form.resetFields();
          }}
        />
      </Modal>

      <Modal
        title={
          <Space>
            <HistoryOutlined />
            <Text>执行历史 - {selectedConfig?.name}</Text>
          </Space>
        }
        open={historyVisible}
        onCancel={() => {
          setHistoryVisible(false);
          setExecutions([]);
        }}
        footer={null}
        width={800}
      >
        <Table
          columns={historyColumns}
          dataSource={executions}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          size="small"
          locale={{ emptyText: <Empty description="暂无执行记录" /> }}
        />
      </Modal>

      <Drawer
        title="执行详情"
        placement="right"
        width={700}
        onClose={() => {
          setDetailVisible(false);
          setRawResults([]);
        }}
        open={detailVisible}
      >
        {executionDetail && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="状态" span={2}>
                {renderStatusTag(executionDetail.status)}
              </Descriptions.Item>
              <Descriptions.Item label="总请求数">{executionDetail.total_requests}</Descriptions.Item>
              <Descriptions.Item label="成功数">{executionDetail.success_count}</Descriptions.Item>
              <Descriptions.Item label="失败数">{executionDetail.failed_count}</Descriptions.Item>
              <Descriptions.Item label="错误率">{executionDetail.error_rate}%</Descriptions.Item>
              <Descriptions.Item label="最小响应">{executionDetail.min_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="最大响应">{executionDetail.max_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="平均响应">{executionDetail.avg_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="P50">{executionDetail.p50_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="P90">{executionDetail.p90_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="P95">{executionDetail.p95_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="P99">{executionDetail.p99_response_time}ms</Descriptions.Item>
              <Descriptions.Item label="吞吐量">{executionDetail.throughput} RPS</Descriptions.Item>
              <Descriptions.Item label="峰值并发">{executionDetail.peak_concurrent}</Descriptions.Item>
              <Descriptions.Item label="执行耗时">{executionDetail.duration_seconds}s</Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {executionDetail.started_at ? moment(executionDetail.started_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {executionDetail.finished_at ? moment(executionDetail.finished_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
            </Descriptions>
            
            <ResponseTimeChart 
              executionDetail={executionDetail}
              results={rawResults}
            />
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default PressureTestManager;