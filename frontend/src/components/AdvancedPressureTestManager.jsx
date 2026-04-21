/**
 * 高级压测管理页面组件
 * 基于Locust的分布式压测功能
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Button, Input, InputNumber, Select, Card, Space, Typography,
  Alert, message, Tag, Table, Tooltip, Empty,
  Statistic, Row, Col, Form, Descriptions, Modal, Breadcrumb, Switch
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined,
  ReloadOutlined, EyeOutlined, PlusOutlined,
  CheckCircleOutlined,
  SyncOutlined, CloudServerOutlined,
  HistoryOutlined, ProjectOutlined, HomeOutlined
} from '@ant-design/icons';
import { advancedPressureTestAPI } from '../api/advancedPressureTest';
import { projectsAPI } from '../api/projects';
import { useAdvancedPressureTestWebSocket } from '../hooks/useAdvancedPressureTestWebSocket';

const { Text, Title } = Typography;
const { Option } = Select;

const AdvancedPressureTestManager = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [formVisible, setFormVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [historyVisible, setHistoryVisible] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [webUiVisible, setWebUiVisible] = useState(false);
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [logModalContent, setLogModalContent] = useState('');
  const [webUiUrl, setWebUiUrl] = useState(null);

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
    setWebUiUrl(null);

    try {
      const response = await advancedPressureTestAPI.config.execute(config.id);
      if (response.data?.execution_id || response.data?.data?.execution_id) {
        const execId = response.data?.execution_id || response.data?.data?.execution_id;
        const uiUrl = response.data?.web_ui_url || response.data?.data?.web_ui_url;
        
        message.info('正在启动高级压测...');
        wsState.connect(execId);
        
        if (uiUrl) {
          setWebUiUrl(uiUrl);
          message.info(`Locust Web UI 已启用: ${uiUrl}`);
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

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (selectedProjectId) {
      setConfigs([]);
    }
  }, [selectedProjectId]);

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
          <Card title="执行监控" extra={
            webUiUrl && (
              <Button 
                icon={<EyeOutlined />}
                onClick={() => setWebUiVisible(true)}
              >
                查看 Locust UI
              </Button>
            )
          }>
            {!wsState.running && !wsState.summary && wsState.connected && (
              <>
                <Alert
                  type="success"
                  message={<Space><CheckCircleOutlined /> 已连接，准备就绪</Space>}
                  description={`配置: ${selectedConfig.name} | 目标: ${selectedConfig.host}`}
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
                {webUiUrl && (
                  <Alert
                    type="info"
                    message="Locust Web UI 已启用"
                    description={`可在 Locust UI 中查看实时监控: ${webUiUrl}`}
                    style={{ marginTop: 16 }}
                  />
                )}
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
                            <Statistic 
                              title={name} 
                              value={data.requests} 
                              suffix={`请求 | ${data.failures}失败`}
                            />
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </div>
                )}
                
                <Button 
                  type="primary" 
                  style={{ marginTop: 16 }}
                  onClick={() => {
                    setSelectedConfig(null);
                    wsState.reset();
                    setWebUiUrl(null);
                  }}
                >
                  返回配置列表
                </Button>
              </Card>
            )}

            {wsState.error && (
              <Alert
                type="error"
                message="执行出错"
                description={wsState.error}
                style={{ marginTop: 16 }}
              />
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
        title={editingConfig ? "编辑高级压测配置" : "新建高级压测配置"}
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          setEditingConfig(null);
          form.resetFields();
        }}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={editingConfig || {
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
            { title: '状态', dataIndex: 'status', key: 'status', render: (s) => <Tag color={s === 'completed' ? 'green' : 'blue'}>{s}</Tag> },
            { title: '总请求', dataIndex: 'total_requests', key: 'total_requests' },
            { title: '成功率', key: 'success_rate', render: (_, r) => r.total_requests > 0 ? `${((r.success_count / r.total_requests) * 100).toFixed(1)}%` : '0%' },
            { title: '开始时间', dataIndex: 'started_at', key: 'started_at' },
            { title: '操作', key: 'action', render: (_, r) => (
              <Button size="small" onClick={() => handleViewLogs(r.id)}>日志</Button>
            )},
          ]}
          locale={{ emptyText: '暂无执行记录' }}
        />
      </Modal>

      {/* Locust Web UI iframe Modal */}
      <Modal
        title="Locust Web UI 实时监控"
        open={webUiVisible}
        onCancel={() => setWebUiVisible(false)}
        footer={null}
        width={1200}
        style={{ top: 20 }}
      >
        {webUiUrl && (
          <div style={{ height: '600px', border: '1px solid #d9d9d9', borderRadius: 4 }}>
            <iframe
              src={webUiUrl}
              style={{ width: '100%', height: '100%', border: 'none' }}
              title="Locust Web UI"
            />
          </div>
        )}
      </Modal>

      {/* 执行日志弹窗 */}
      <Modal
        title="执行日志"
        open={logModalVisible}
        onCancel={() => setLogModalVisible(false)}
        footer={[<Button key="close" onClick={() => setLogModalVisible(false)}>关闭</Button>]}
        width={800}
      >
        <Card style={{ background: '#f5f5f5', maxHeight: 500, overflow: 'auto' }}>
          <pre style={{ fontFamily: 'monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap' }}>
            {logModalContent}
          </pre>
        </Card>
      </Modal>
    </div>
  );
};

export default AdvancedPressureTestManager;