import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  Descriptions,
  Modal,
  Switch,
  Tooltip,
  message,
  Alert,
  Popconfirm,
  notification
} from 'antd';
import {
  HolderOutlined,
  SettingOutlined,
  DeleteOutlined,
  PlusOutlined,
  EditOutlined,
  PlayCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { JSONPath } from 'jsonpath-plus';
import '../css/RequestCollectionManager.css';

const { Title } = Typography;

// 拖拽行组件
const DraggableRow = ({ index, moveRow, className, style, ...restProps }) => {
  const ref = React.useRef(null);
  const [{ isOver, dropClassName }, drop] = useDrop({
    accept: 'DraggableRow',
    collect: monitor => {
      const { index: dragIndex } = monitor.getItem() || {};
      if (dragIndex === index) {
        return {};
      }
      return {
        isOver: monitor.isOver(),
        dropClassName: dragIndex < index ? ' drop-over-downward' : ' drop-over-upward',
      };
    },
    drop: item => {
      moveRow(item.index, index);
    },
  });
  const [, drag] = useDrag({
    type: 'DraggableRow',
    item: { index },
    collect: monitor => ({
      isDragging: monitor.isDragging(),
    }),
  });

  drop(drag(ref));

  return (
    <tr
      ref={ref}
      className={`${className}${isOver ? dropClassName : ''}`}
      style={{ ...style }}
      {...restProps}
    />
  );
};

function RequestCollectionManager() {
  const [collections, setCollections] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(new Set());
  const [executionResult, setExecutionResult] = useState(null);

  // Modal 状态
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [selectedRequestIds, setSelectedRequestIds] = useState([]);
  const [collectionRequests, setCollectionRequests] = useState([]);

  // 提取规则 Modal 状态
  const [extractModal, setExtractModal] = useState({
    visible: false,
    index: null,
    sampleData: null,
  });

  const [form] = Form.useForm();
  const prevModeRef = useRef(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [collectionsRes, requestsRes] = await Promise.all([
        apiClient.get('/request-collections/'),
        apiClient.get('/api-requests/'),
      ]);

      setCollections(collectionsRes.data.results || []);
      setRequests(requestsRes.data.results || []);
      setLoading(false);
    } catch (error) {
      notification.error({ message: '获取数据失败', description: error.message });
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 打开创建/编辑 Modal
  const openModal = async (record = null) => {
    setEditingRecord(record);

    if (record) {
      // 编辑模式：加载详情和 collection_requests
      try {
        const detailRes = await apiClient.get(`/request-collections/${record.id}/`);
        const detail = detailRes.data;

        form.setFieldsValue({
          name: detail.name,
          description: detail.description,
          execution_mode: detail.execution_mode,
          requests: detail.requests || [],
        });

        setSelectedRequestIds(detail.requests || []);
        setCollectionRequests((detail.collection_requests || []).map(req => ({
          ...req,
          request_count: req.request_count || 1
        })));
        prevModeRef.current = detail.execution_mode;
      } catch (error) {
        message.error('加载详情失败');
      }
    } else {
      // 创建模式
      form.resetFields();
      setSelectedRequestIds([]);
      setCollectionRequests([]);
      prevModeRef.current = null;
    }

    setModalVisible(true);
  };

  // 关闭 Modal
  const closeModal = () => {
    setModalVisible(false);
    setEditingRecord(null);
    setSelectedRequestIds([]);
    setCollectionRequests([]);
    prevModeRef.current = null;
    form.resetFields();
  };

  // 处理模式切换
  const handleModeChange = (newMode) => {
    const prevMode = prevModeRef.current;

    if (!prevMode || prevMode === newMode) {
      prevModeRef.current = newMode;
      return;
    }

    // 顺序/链式 -> 并发：提示会失去排序信息
    if ((prevMode === 'sequential' || prevMode === 'chain') && newMode === 'concurrent') {
      Modal.confirm({
        title: '切换执行模式',
        icon: <ExclamationCircleOutlined />,
        content: '切换到并发模式后，已设置的请求顺序和变量提取规则将失效，确认切换？',
        okText: '确认',
        cancelText: '取消',
        onCancel: () => {
          form.setFieldValue('execution_mode', prevMode);
        },
      });
    }

    // 并发 -> 顺序/链式：提示需要配置
    if (prevMode === 'concurrent' && (newMode === 'sequential' || newMode === 'chain')) {
      Modal.info({
        title: '提示',
        content: '切换到顺序/链式模式后，请在下方配置请求执行顺序',
      });
    }

    prevModeRef.current = newMode;
  };

  // 保存集合
  const handleSave = async (values) => {
    try {
      const payload = {
        name: values.name,
        description: values.description || '',
        execution_mode: values.execution_mode,
        requests: selectedRequestIds,
        project: 1, // 默认项目ID
      };

      // 如果 collectionRequests 有数据，添加 collection_requests 配置
      if (collectionRequests.length > 0) {
        payload.collection_requests = collectionRequests.map((req, index) => ({
          api_request: req.api_request,
          order_index: index,
          stop_on_failure: values.execution_mode !== 'concurrent' ? (req.stop_on_failure !== false) : false,
          extract_rules: values.execution_mode === 'chain' ? (req.extract_rules || []) : [],
          request_count: req.request_count || 1,
        }));
      }

      if (editingRecord) {
        await apiClient.patch(`/request-collections/${editingRecord.id}/`, payload);
        message.success('更新成功');
      } else {
        await apiClient.post('/request-collections/', payload);
        message.success('创建成功');
      }

      closeModal();
      loadData();
    } catch (error) {
      message.error('保存失败：' + (error.response?.data?.detail || error.message));
    }
  };

  // 删除集合
  const handleDelete = async (id) => {
    try {
      await apiClient.delete(`/request-collections/${id}/`);
      message.success('删除成功');
      loadData();
    } catch (error) {
      message.error('删除失败：' + error.message);
    }
  };

  // 执行集合
  const handleExecute = async (collectionId) => {
    setExecuting(prev => new Set(prev).add(collectionId));
    setExecutionResult(null);
    try {
      const response = await apiClient.post(`/request-collections/${collectionId}/execute/`);
      setExecutionResult(response.data);
      message.success('集合执行完成');
    } catch (error) {
      message.error('执行失败：' + error.message);
    } finally {
      setExecuting(prev => {
        const newSet = new Set(prev);
        newSet.delete(collectionId);
        return newSet;
      });
    }
  };

  // 处理选择的请求变化
  const handleRequestsChange = (newSelectedIds) => {
    setSelectedRequestIds(newSelectedIds);

    // 所有模式下都要更新 collectionRequests
    const mode = form.getFieldValue('execution_mode');
    const newCollectionRequests = newSelectedIds.map((id, index) => {
      const existing = collectionRequests.find(cr => cr.api_request === id);
      return {
        api_request: id,
        order_index: index,
        stop_on_failure: existing?.stop_on_failure ?? true,
        extract_rules: existing?.extract_rules || [],
        request_count: existing?.request_count || 1,
      };
    });
    setCollectionRequests(newCollectionRequests);
  };

  // 拖拽排序
  const moveRow = useCallback((dragIndex, hoverIndex) => {
    const newData = [...collectionRequests];
    const dragRow = newData[dragIndex];
    newData.splice(dragIndex, 1);
    newData.splice(hoverIndex, 0, dragRow);

    // 重新计算 order_index
    const reordered = newData.map((item, idx) => ({
      ...item,
      order_index: idx
    }));

    setCollectionRequests(reordered);
  }, [collectionRequests]);

  // 删除集合中的请求
  const removeFromCollection = (index) => {
    const requestToRemove = collectionRequests[index];
    const newSelectedIds = selectedRequestIds.filter(id => id !== requestToRemove.api_request);
    const newCollectionRequests = collectionRequests.filter((_, i) => i !== index);
    const reordered = newCollectionRequests.map((item, idx) => ({
      ...item,
      order_index: idx
    }));

    setSelectedRequestIds(newSelectedIds);
    setCollectionRequests(reordered);
    form.setFieldValue('requests', newSelectedIds);
  };

  // 配置提取规则
  const openExtractModal = async (index) => {
    const request = collectionRequests[index];
    const requestDetail = requests.find(r => r.id === request.api_request);

    // 尝试获取最近一次成功的响应作为示例数据
    let sampleData = null;
    try {
      const historyRes = await apiClient.get(`/api-requests/${request.api_request}/history/?limit=1`);
      if (historyRes.data.results && historyRes.data.results.length > 0) {
        const lastResult = historyRes.data.results[0];
        // 兼容后端返回的字段名（response_status）
        const statusCode = lastResult.response_status || lastResult.status_code;
        if (statusCode >= 200 && statusCode < 300) {
          try {
            sampleData = JSON.parse(lastResult.response_body || '{}');
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    } catch (e) {
      // 忽略错误
    }

    setExtractModal({
      visible: true,
      index,
      sampleData,
    });
  };

  const saveExtractRules = (rules) => {
    const newCollectionRequests = [...collectionRequests];
    newCollectionRequests[extractModal.index].extract_rules = rules;
    setCollectionRequests(newCollectionRequests);

    setExtractModal({
      visible: false,
      index: null,
      sampleData: null,
    });

    message.success('提取规则保存成功');
  };

  const executionMode = Form.useWatch('execution_mode', form);

  // 列定义 - 使用useMemo优化
  const columns = React.useMemo(() => [
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '模式',
      dataIndex: 'execution_mode',
      key: 'execution_mode',
      width: 120,
      render: (mode) => ({
        'concurrent': <span className="request-collection-mode-concurrent">并发</span>,
        'sequential': <span className="request-collection-mode-sequential">顺序</span>,
        'chain': <span className="request-collection-mode-chain">链式</span>,
      }[mode] || mode),
    },
    { title: '请求数', dataIndex: 'request_count', key: 'request_count', align: 'center', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => openModal(record)}
            />
          </Tooltip>
          <Tooltip title="执行">
            <Button
              type="text"
              icon={<PlayCircleOutlined className="request-collection-execute-icon" />}
              onClick={() => handleExecute(record.id)}
              loading={executing.has(record.id)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定删除该集合？"
              onConfirm={() => handleDelete(record.id)}
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ], [openModal, handleExecute, executing, handleDelete]);

  return (
    <div className="request-collection-container">
      <Space className="request-collection-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => openModal()}
        >
          创建请求集合
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={collections}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      {executionResult && (
        <Card
          title={
            <Space>
              <PlayCircleOutlined style={{ color: '#52c41a' }} />
              <span>执行结果</span>
            </Space>
          }
          className="request-collection-execution-card"
          loading={executing.size > 0}
        >
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="状态">
              <span className={
                executionResult.status === 'success' ? 'request-collection-status-text' :
                executionResult.status === 'running' ? 'request-collection-status-text-running' : 
                'request-collection-status-text-error'
              }>
                {executionResult.status}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label="通过率">{executionResult.pass_rate}%</Descriptions.Item>
            <Descriptions.Item label="通过数">{executionResult.passed_requests}</Descriptions.Item>
            <Descriptions.Item label="失败数">{executionResult.failed_requests}</Descriptions.Item>
          </Descriptions>

          {executionResult.output && (
            <>
              <Title level={5} className="request-collection-output-title">详细输出</Title>
              <Card className="request-collection-output-card">
                <pre className="request-collection-output-pre">{executionResult.output}</pre>
              </Card>
            </>
          )}
        </Card>
      )}

      {/* 编辑/创建 Modal */}
      <Modal
        title={editingRecord ? '编辑请求集合' : '创建请求集合'}
        open={modalVisible}
        onCancel={closeModal}
        onOk={() => form.submit()}
        width={800}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            execution_mode: 'concurrent',
          }}
        >
          <Form.Item
            name="name"
            label="集合名称"
            rules={[{ required: true, message: '请输入集合名称' }]}
          >
            <Input placeholder="请输入集合名称" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="请输入集合描述（可选）" />
          </Form.Item>

          <Form.Item
            name="execution_mode"
            label="执行模式"
            rules={[{ required: true }]}
          >
            <Select
              onChange={handleModeChange}
              options={[
                { label: '并发执行', value: 'concurrent', title: '所有请求同时执行' },
                { label: '顺序执行', value: 'sequential', title: '请求按顺序逐个执行' },
                { label: '链式执行（支持变量传递）', value: 'chain', title: '请求按顺序执行，支持变量提取和传递' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="选择请求"
            required
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="请选择要包含的API请求"
              value={selectedRequestIds}
              onChange={handleRequestsChange}
              options={requests.map(req => ({
                label: `${req.name} (${req.method})`,
                value: req.id,
                title: req.url,
              }))}
              filterOption={(input, option) =>
                option.label.toLowerCase().includes(input.toLowerCase())
              }
              style={{ marginBottom: 16 }}
            />

            {/* 请求配置表格 */}
            {selectedRequestIds.length > 0 && (
              <>
                {executionMode !== 'concurrent' && (
                  <Alert
                    message="拖拽下方列表可调整请求执行顺序"
                    type="info"
                    showIcon
                    style={{ marginBottom: 8 }}
                  />
                )}
                {executionMode !== 'concurrent' ? (
                  <DndProvider backend={HTML5Backend}>
                    <Table
                      size="small"
                      pagination={false}
                      dataSource={collectionRequests}
                      rowKey="api_request"
                      components={{
                        body: {
                          row: (props) => <DraggableRow {...props} moveRow={moveRow} />
                        }
                      }}
                      scroll={{ x: 'max-content' }}
                    >
                      <Table.Column
                        title=""
                        width={30}
                        render={() => <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />}
                      />
                      <Table.Column
                        title=""
                        width={60}
                        render={(_, __, index) => <span>{index + 1}</span>}
                      />
                      <Table.Column
                        title="请求名称"
                        render={(record) => {
                          const req = requests.find(r => r.id === record.api_request);
                          return req ? `${req.name} (${req.method})` : '-';
                        }}
                      />
                      <Table.Column
                        title="请求次数"
                        width={100}
                        align="center"
                        render={(_, record, index) => (
                          <Input
                            type="number"
                            min={1}
                            max={1000}
                            value={record.request_count || 1}
                            onChange={(e) => {
                              const value = parseInt(e.target.value) || 1;
                              const newData = [...collectionRequests];
                              newData[index].request_count = Math.min(1000, Math.max(1, value));
                              setCollectionRequests(newData);
                            }}
                            style={{ width: 70 }}
                          />
                        )}
                      />
                      <Table.Column
                        title="失败即停"
                        width={100}
                        align="center"
                        render={(_, record, index) => (
                          <Switch
                            size="small"
                            checked={record.stop_on_failure !== false}
                            onChange={(checked) => {
                              const newData = [...collectionRequests];
                              newData[index].stop_on_failure = checked;
                              setCollectionRequests(newData);
                            }}
                          />
                        )}
                      />
                      {executionMode === 'chain' && (
                        <Table.Column
                          title="变量提取"
                          width={100}
                          align="center"
                          render={(_, record, index) => {
                            const ruleCount = record.extract_rules?.length || 0;
                            return (
                              <Tooltip title={ruleCount > 0 ? `已配置 ${ruleCount} 条规则` : '点击配置'}>
                                <Button
                                  type={ruleCount > 0 ? 'primary' : 'default'}
                                  size="small"
                                  icon={<SettingOutlined />}
                                  onClick={() => openExtractModal(index)}
                                >
                                  {ruleCount > 0 ? ruleCount : '配置'}
                                </Button>
                              </Tooltip>
                            );
                          }}
                        />
                      )}
                      <Table.Column
                        title="操作"
                        width={80}
                        align="center"
                        render={(_, record, index) => (
                          <Popconfirm
                            title="确定要移除该请求吗？"
                            onConfirm={() => removeFromCollection(index)}
                          >
                            <Button type="link" danger size="small">
                              移除
                            </Button>
                          </Popconfirm>
                        )}
                      />
                    </Table>
                  </DndProvider>
                ) : (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={collectionRequests}
                    rowKey="api_request"
                    scroll={{ x: 'max-content' }}
                  >
                  {executionMode !== 'concurrent' && (
                    <Table.Column
                      title=""
                      width={30}
                      render={() => <HolderOutlined style={{ cursor: 'grab', color: '#999' }} />}
                    />
                  )}
                  <Table.Column
                    title=""
                    width={60}
                    render={(_, __, index) => <span>{index + 1}</span>}
                  />
                  <Table.Column
                    title="请求名称"
                    render={(record) => {
                      const req = requests.find(r => r.id === record.api_request);
                      return req ? `${req.name} (${req.method})` : '-';
                    }}
                  />
                  <Table.Column
                    title="请求次数"
                    width={100}
                    align="center"
                    render={(_, record, index) => (
                      <Input
                        type="number"
                        min={1}
                        max={1000}
                        value={record.request_count || 1}
                        onChange={(e) => {
                          const value = parseInt(e.target.value) || 1;
                          const newData = [...collectionRequests];
                          newData[index].request_count = Math.min(1000, Math.max(1, value));
                          setCollectionRequests(newData);
                        }}
                        style={{ width: 70 }}
                      />
                    )}
                  />
                  {executionMode !== 'concurrent' && (
                    <Table.Column
                      title="失败即停"
                      width={100}
                      align="center"
                      render={(_, record, index) => (
                        <Switch
                          size="small"
                          checked={record.stop_on_failure !== false}
                          onChange={(checked) => {
                            const newData = [...collectionRequests];
                            newData[index].stop_on_failure = checked;
                            setCollectionRequests(newData);
                          }}
                        />
                      )}
                    />
                  )}
                  {executionMode === 'chain' && (
                    <Table.Column
                      title="变量提取"
                      width={100}
                      align="center"
                      render={(_, record, index) => {
                        const ruleCount = record.extract_rules?.length || 0;
                        return (
                          <Tooltip title={ruleCount > 0 ? `已配置 ${ruleCount} 条规则` : '点击配置'}>
                            <Button
                              type={ruleCount > 0 ? 'primary' : 'default'}
                              size="small"
                              icon={<SettingOutlined />}
                              onClick={() => openExtractModal(index)}
                            >
                              {ruleCount > 0 ? ruleCount : '配置'}
                            </Button>
                          </Tooltip>
                        );
                      }}
                    />
                  )}
                  <Table.Column
                    title="操作"
                    width={80}
                    align="center"
                    render={(_, __, index) => (
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeFromCollection(index)}
                      >
                        删除
                      </Button>
                    )}
                  />
                </Table>
                )}
                {executionMode === 'concurrent' && (
                  <Alert
                    message="提示：在并发模式下，设置的请求次数表示该请求会被并发执行的次数"
                    type="info"
                    showIcon
                    style={{ marginTop: 8 }}
                  />
                )}
              </>
            )}
          </Form.Item>

          {executionMode === 'concurrent' && (
            <Alert
              message="并发模式下执行顺序随机，无需配置请求顺序"
              type="warning"
              showIcon
            />
          )}
        </Form>
      </Modal>

      {/* 提取规则配置 Modal */}
      <Modal
        title="配置变量提取规则"
        open={extractModal.visible}
        onCancel={() => setExtractModal({ visible: false, index: null, sampleData: null })}
        onOk={() => {
          const form = document.getElementById('extract-rules-form');
          if (form) {
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
          }
        }}
        width={700}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Alert
          message="链式执行模式下，提取的变量可在后续请求的 URL/Header/Body 中使用，格式: {{变量名}}"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {extractModal.sampleData && (
          <Alert
            message="提示：已加载最近一次成功响应作为示例数据，可在下方输入 JSONPath 进行测试"
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          id="extract-rules-form"
          initialValues={{ rules: collectionRequests[extractModal.index]?.extract_rules || [] }}
          onFinish={(values) => saveExtractRules(values.rules)}
        >
          <Form.List name="rules">
            {(fields, { add, remove }, { errors }) => (
              <>
                {fields.map(({ key, name, ...restField }) => {
                  // 使用普通函数测试，而不是 React Hook
                  const testJsonPath = (jsonpath) => {
                    if (!jsonpath || !extractModal.sampleData) return null;
                    try {
                      const result = JSONPath({ path: jsonpath, json: extractModal.sampleData });
                      return result && result.length > 0 ? result[0] : null;
                    } catch (e) {
                      return null;
                    }
                  };

                  return (
                    <Row key={key} gutter={8} style={{ marginBottom: 8 }} align="middle">
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'name']}
                          rules={[
                            { required: true, message: '变量名不能为空' },
                            { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/, message: '变量名格式错误' }
                          ]}
                          style={{ marginBottom: 0 }}
                        >
                          <Input placeholder="变量名" addonBefore="{{" addonAfter="}}" />
                        </Form.Item>
                      </Col>
                      <Col span={11}>
                        <Form.Item
                          {...restField}
                          name={[name, 'jsonpath']}
                          rules={[{ required: true, message: 'JSONPath 不能为空' }]}
                          style={{ marginBottom: 0 }}
                        >
                          <Input placeholder="JSONPath 表达式，如: $.data.token" />
                        </Form.Item>
                      </Col>
                      <Col span={4}>
                        <Form.Item shouldUpdate style={{ marginBottom: 0 }}>
                          {() => {
                            const jsonpath = form.getFieldValue(['rules', name, 'jsonpath']);
                            const testResult = testJsonPath(jsonpath);
                            return (
                              extractModal.sampleData && (
                                <Tooltip title={testResult !== null ? `测试结果: ${JSON.stringify(testResult)}` : '表达式无效或匹配不到数据'}>
                                  <span style={{ color: testResult !== null ? '#52c41a' : '#ff4d4f', fontSize: 16 }}>
                                    {testResult !== null ? '✓' : '✗'}
                                  </span>
                                </Tooltip>
                              )
                            );
                          }}
                        </Form.Item>
                      </Col>
                      <Col span={3} style={{ textAlign: 'center' }}>
                        <DeleteOutlined onClick={() => remove(name)} style={{ color: '#ff4d4f', cursor: 'pointer' }} />
                      </Col>
                    </Row>
                  );
                })}

                <Button type="dashed" onClick={() => add()} block style={{ marginTop: 8 }}>
                  <PlusOutlined /> 添加提取规则
                </Button>
                <Form.ErrorList errors={errors} />
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

export default RequestCollectionManager;
