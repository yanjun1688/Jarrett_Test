/**
 * 高级压测管理页面组件
 * 基于Locust的分布式压测功能
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Button, Input, InputNumber, Select, Card, Space, Typography,
  Alert, message, Tag, Popconfirm, Table, Tooltip, Empty, Progress,
  Statistic, Row, Col, Form, Descriptions, Modal, Breadcrumb, Switch
} from 'antd';
import {
  ThunderboltOutlined, PlayCircleOutlined, PauseCircleOutlined,
  DeleteOutlined, ReloadOutlined, EyeOutlined, PlusOutlined,
  EditOutlined, ClockCircleOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SyncOutlined, CloudServerOutlined,
  HistoryOutlined, ProjectOutlined, HomeOutlined, RocketOutlined
} from '@ant-design/icons';
import { advancedPressureTestAPI } from '../api/advancedPressureTest';
import { apiRequestsAPI } from '../api/apiRequests';
import { projectsAPI } from '../api/projects';
import { useAdvancedPressureTestWebSocket } from '../hooks/useAdvancedPressureTestWebSocket';
import moment from 'moment';

const { Text, Title } = Typography;
const { Option } = Select;

const STATUS_MAP = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  stopped: { color: 'warning', icon: <PauseCircleOutlined />, text: '已停止' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
};

const renderStatusTag = (status) => {
  const config = STATUS_MAP[status] || STATUS_MAP.pending;
  return (
    <Tag icon={config.icon} color={config.color}>
      {config.text}
    </Tag>
  );
};

const AdvancedPressureTestManager = () => {
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

  const getToken = () => localStorage.getItem('authToken');
  const wsState = useAdvancedPressureTestWebSocket(getToken());

  const loadProjects = useCallback(async () => {
    try {
      const response = await projectsAPI.getAll();
      const projectList = response.data?.results || response.data?.data?.results || response.data || [];
      setProjects(Array.isArray(projectList) ? projectList : []);
    } catch (error) {
      message.error('加载项目列表失败: ' + (error.response?.data?.error || error.message));
    }
  }, []);

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

  const loadApiRequests = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const response = await apiRequestsAPI.getAll({ project: selectedProjectId });
      const data = response.data?.results || response.data?.data?.results || response.data || [];
      setApiRequests(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Load API requests error:', error);
      setApiRequests([]);
    }
  }, [selectedProjectId]);

  const handleCreateConfig = async (values) => {
    try {
      const data = { ...values, project: selectedProjectId };
      const response = await advancedPressureTestAPI.config.create(data);
      if (response.status === 201 || response.data?.id) {
        message.success('配置创建成功');
        setFormVisible(false);
        form.resetFields();
        await loadConfigs();
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message;
      message.error('创建失败: ' + errorMsg);
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
        
        if (response.data?.web_ui_url || response.data?.data?.web_ui_url) {
          const webUiUrl = response.data?.web_ui_url || response.data?.data?.web_ui_url;
          message.info(`Locust Web UI: ${webUiUrl}`);
        }
      }
    } catch (error) {
      message.error('执行失败: ' + (error.response?.data?.error || error.message));
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

  const handleViewHistory = async (config) => {
    setSelectedConfig(config);
    setHistoryVisible(true);
    try {
      const response = await advancedPressureTestAPI.config.getHistory(config.id);
      if (response.data) {
        setExecutions(response.data?.data || response.data || []);
      }
    } catch (error) {
      message.error('加载历史失败: ' + (error.response?.data?.error || error.message));
    }
  };

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (selectedProjectId) {
      loadApiRequests();
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
      title: '用户数',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (val) => `${val}用户`
    },
    {
      title: '启动速率',
      dataIndex: 'spawn_rate',
      key: 'spawn_rate',
      render: (val) => `${val}/s`
    },
    {
      title: '持续时间',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      render: (val) => `${val}秒`
    },
    {
      title: '分布式',
      dataIndex: 'use_distributed',
      key: 'use_distributed',
      render: (val) => val ? <Tag color="blue">是</Tag> : <Tag>否</Tag>
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
          <Tooltip title="历史记录">
            <Button 
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record)}
              size="small"
            />
          </Tooltip>
        </Space>
      )
    }
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

        {/* 监控面板 */}
        {selectedConfig && (
          <Card title="执行监控">
            {!wsState.running && !wsState.summary && wsState.connected && (
              <>
                <Alert
                  type="success"
                  message={<Space><CheckCircleOutlined /> 已连接，准备就绪</Space>}
                  description={`配置: ${selectedConfig.name}`}
                  style={{ marginBottom: 16 }}
                />
                <Button
                  type="primary"
                  size="large"
                  icon={<PlayCircleOutlined />}
                  onClick={handleStart}
                  block
                >
                  开始压测
                </Button>
                {selectedConfig.enable_web_ui && (
                  <Alert
                    type="info"
                    message="Locust Web UI"
                    description={`访问地址: http://localhost:${selectedConfig.web_ui_port}`}
                    style={{ marginTop: 16 }}
                  />
                )}
              </>
            )}

            {wsState.running && wsState.stats && (
              <>
                <Alert
                  type="info"
                  message={<Space><SyncOutlined spin /> 正在执行</Space>}
                  style={{ marginBottom: 16 }}
                />
                <Progress 
                  percent={Math.round((wsState.stats.total_requests / (selectedConfig.user_count * 10)) * 100)}
                  status="active"
                />
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={4}>
                    <Statistic title="用户数" value={wsState.stats.current_users} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="RPS" value={wsState.stats.rps?.toFixed(2) || 0} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="成功率" value={100 - (wsState.stats.fail_ratio || 0)} suffix="%" />
                  </Col>
                  <Col span={4}>
                    <Statistic title="平均响应" value={wsState.stats.avg_response_time?.toFixed(2) || 0} suffix="ms" />
                  </Col>
                  <Col span={4}>
                    <Statistic title="总请求" value={wsState.stats.total_requests} />
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
                <Descriptions bordered column={3} size="small">
                  <Descriptions.Item label="总请求数">{wsState.summary.total_requests}</Descriptions.Item>
                  <Descriptions.Item label="成功数">{wsState.summary.success_count}</Descriptions.Item>
                  <Descriptions.Item label="失败数">{wsState.summary.failed_count}</Descriptions.Item>
                  <Descriptions.Item label="错误率">{wsState.summary.error_rate}%</Descriptions.Item>
                  <Descriptions.Item label="平均响应">{wsState.summary.avg_response_time}ms</Descriptions.Item>
                  <Descriptions.Item label="吞吐量">{wsState.summary.throughput} RPS</Descriptions.Item>
                </Descriptions>
              </Card>
            )}
          </Card>
        )}

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
                    : "暂无配置，点击「新建配置」创建"
                } 
              /> 
            }}
          />
        </Card>
      </Space>

      <Modal
        title="新建高级压测配置"
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            user_count: 100,
            spawn_rate: 10,
            duration_seconds: 60,
            use_distributed: false,
            worker_count: 1,
            web_ui_port: 18089,
            enable_web_ui: true
          }}
          onFinish={handleCreateConfig}
        >
          <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
            <Input placeholder="例如：Locust压测配置" />
          </Form.Item>

          <Form.Item name="host" label="目标地址" rules={[{ required: true }]}>
            <Input placeholder="http://localhost:8080" />
          </Form.Item>

          <Form.Item name="user_count" label="并发用户数" rules={[{ required: true }]}>
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="spawn_rate" label="启动速率(用户/秒)" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="duration_seconds" label="持续时间(秒)" rules={[{ required: true }]}>
            <InputNumber min={1} max={3600} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="use_distributed" valuePropName="checked" label="启用分布式">
            <Switch />
          </Form.Item>

          <Form.Item name="worker_count" label="Worker数量">
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="enable_web_ui" valuePropName="checked" label="启用Web UI">
            <Switch />
          </Form.Item>

          <Form.Item name="web_ui_port" label="Web UI端口">
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">创建</Button>
              <Button onClick={() => setFormVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdvancedPressureTestManager;