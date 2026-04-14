import React, { useState, useEffect, useRef } from 'react';
import { Modal, Form, Input, Select, Table, Switch, Tag, Space, Divider, Alert, Steps } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import apiClient from '../../api/axios';
import VariablesConfig from '../VariablesConfig';
import PreActionConfig from './shared/PreActionConfig';
import ExtractRulesModalContent from './shared/ExtractRulesModalContent';
import AssertionConfig from './shared/AssertionConfig';

const REQUEST_TYPE_OPTIONS = [
  { value: 'setup', label: 'Setup' },
  { value: 'normal', label: 'Normal' },
  { value: 'teardown', label: 'Teardown' },
];

const CollectionFormModal = ({
  visible,
  editingRecord,
  onClose,
  onSave,
  requests = [],
}) => {
  const [form] = Form.useForm();
  const [selectedRequestIds, setSelectedRequestIds] = useState([]);
  const [collectionRequests, setCollectionRequests] = useState([]);
  const [sampleDataMap, setSampleDataMap] = useState({});
  const [expandedRowKeys, setExpandedRowKeys] = useState([]);
  const loadedSamplesRef = useRef(new Set());

  const executionMode = Form.useWatch('execution_mode', form);

  useEffect(() => {
    if (visible && editingRecord) {
      form.setFieldsValue({
        name: editingRecord.name,
        description: editingRecord.description,
        execution_mode: editingRecord.execution_mode,
        variables: editingRecord.variables || [],
      });
      setSelectedRequestIds(editingRecord.requests || []);
      setCollectionRequests((editingRecord.collection_requests || []).map(req => ({
        ...req,
        request_type: req.request_type || 'normal',
        stop_on_failure: req.stop_on_failure !== false,
        pre_actions: req.pre_actions || [],
        extract_rules: req.extract_rules || [],
        assertions: req.assertions || [],
      })));
    } else if (visible) {
      form.resetFields();
      form.setFieldsValue({ execution_mode: 'chain', variables: [] });
      setSelectedRequestIds([]);
      setCollectionRequests([]);
      setSampleDataMap({});
      setExpandedRowKeys([]);
      loadedSamplesRef.current = new Set();
    }
  }, [visible, editingRecord, form]);

  useEffect(() => {
    if (visible && collectionRequests.length > 0) {
      collectionRequests.forEach(cr => {
        if (!loadedSamplesRef.current.has(cr.api_request)) {
          loadedSamplesRef.current.add(cr.api_request);
          loadSampleData(cr.api_request);
        }
      });
    }
  }, [visible, collectionRequests]);

  const loadSampleData = async (apiRequestId) => {
    if (!apiRequestId) return;
    try {
      const historyRes = await apiClient.get(`/api-requests/${apiRequestId}/history/?limit=1`);
      if (historyRes.data.results && historyRes.data.results.length > 0) {
        const lastResult = historyRes.data.results[0];
        const statusCode = lastResult.response_status || lastResult.status_code;
        if (statusCode >= 200 && statusCode < 300) {
          try {
            const data = JSON.parse(lastResult.response_body || '{}');
            setSampleDataMap(prev => ({ ...prev, [apiRequestId]: data }));
          } catch (e) {
            setSampleDataMap(prev => ({ ...prev, [apiRequestId]: null }));
          }
        }
      }
    } catch (e) {
      setSampleDataMap(prev => ({ ...prev, [apiRequestId]: null }));
    }
  };

  const handleRequestsChange = (newSelectedIds) => {
    setSelectedRequestIds(newSelectedIds);
    const newCollectionRequests = newSelectedIds.map((id, index) => {
      const existing = collectionRequests.find(cr => cr.api_request === id);
      return {
        api_request: id,
        order_index: index,
        request_type: existing?.request_type || 'normal',
        stop_on_failure: existing?.stop_on_failure !== false,
        pre_actions: existing?.pre_actions || [],
        extract_rules: existing?.extract_rules || [],
        assertions: existing?.assertions || [],
      };
    });
    setCollectionRequests(newCollectionRequests);
    form.setFieldValue('requests', newSelectedIds);
  };

  const updateRequestType = (index, value) => {
    const newData = [...collectionRequests];
    newData[index].request_type = value;
    setCollectionRequests(newData);
  };

  const updateStopOnFailure = (index, checked) => {
    const newData = [...collectionRequests];
    newData[index].stop_on_failure = checked;
    setCollectionRequests(newData);
  };

  const updatePreActions = (index, value) => {
    const newData = [...collectionRequests];
    newData[index].pre_actions = value;
    setCollectionRequests(newData);
  };

  const updateExtractRules = (index, value) => {
    const newData = [...collectionRequests];
    newData[index].extract_rules = value;
    setCollectionRequests(newData);
  };

  const updateAssertions = (index, value) => {
    const newData = [...collectionRequests];
    newData[index].assertions = value;
    setCollectionRequests(newData);
  };

  const removeRequest = (index) => {
    const requestToRemove = collectionRequests[index];
    const newSelectedIds = selectedRequestIds.filter(id => id !== requestToRemove.api_request);
    const newCollectionRequests = collectionRequests.filter((_, i) => i !== index);
    setSelectedRequestIds(newSelectedIds);
    setCollectionRequests(newCollectionRequests);
    form.setFieldValue('requests', newSelectedIds);
  };

  const getRequestInfo = (apiRequestId) => {
    return requests.find(r => r.id === apiRequestId);
  };

  const getMethodColor = (method) => {
    const colors = {
      GET: 'green',
      POST: 'blue',
      PUT: 'orange',
      DELETE: 'red',
      PATCH: 'purple',
    };
    return colors[method] || 'default';
  };

  const expandedRowRender = (record) => {
    const idx = collectionRequests.findIndex(cr => cr.api_request === record.api_request);
    if (idx === -1) return null;
    
    const sampleData = sampleDataMap[record.api_request];
    const isChainMode = executionMode === 'chain';
    
    const stepItems = [
      {
        title: '前置操作',
        status: 'process',
        description: (
          <div style={{ 
            background: '#e6f7ff', 
            border: '1px solid #91d5ff', 
            borderRadius: 6, 
            padding: 12,
            marginLeft: 24 
          }}>
            <PreActionConfig
              value={collectionRequests[idx].pre_actions}
              onChange={(v) => updatePreActions(idx, v)}
            />
          </div>
        ),
      },
    ];
    
    if (isChainMode) {
      stepItems.push(
        {
          title: '变量提取',
          status: 'process',
          description: (
            <div style={{ 
              background: '#e6f7ff', 
              border: '1px solid #91d5ff', 
              borderRadius: 6, 
              padding: 12,
              marginLeft: 24 
            }}>
              <ExtractRulesModalContent
                value={collectionRequests[idx].extract_rules}
                onChange={(v) => updateExtractRules(idx, v)}
                sampleData={sampleData}
              />
            </div>
          ),
        },
        {
          title: '断言验证',
          status: 'process',
          description: (
            <div style={{ 
              background: '#e6f7ff', 
              border: '1px solid #91d5ff', 
              borderRadius: 6, 
              padding: 12,
              marginLeft: 24 
            }}>
              <AssertionConfig
                value={collectionRequests[idx].assertions}
                onChange={(v) => updateAssertions(idx, v)}
              />
            </div>
          ),
        }
      );
    }
    
    return (
      <div style={{ padding: '16px 24px', background: '#fafafa' }}>
        <Steps
          direction="vertical"
          size="small"
          current={-1}
          items={stepItems}
        />
        {!isChainMode && (
          <Alert 
            message="并发模式下不支持变量提取和断言" 
            type="info" 
            showIcon 
            size="small"
            style={{ marginTop: 12 }}
          />
        )}
      </div>
    );
  };

  const getSummary = (record) => {
    const idx = collectionRequests.findIndex(cr => cr.api_request === record.api_request);
    if (idx === -1) return '';
    
    const cr = collectionRequests[idx];
    const parts = [];
    if (cr.pre_actions?.length) parts.push(`前置${cr.pre_actions.length}`);
    if (cr.extract_rules?.length) parts.push(`提取${cr.extract_rules.length}`);
    if (cr.assertions?.length) parts.push(`断言${cr.assertions.length}`);
    
    return parts.length > 0 ? parts.join(' / ') : '';
  };

  const columns = [
    {
      title: '请求',
      dataIndex: 'api_request',
      key: 'request',
      render: (apiRequestId) => {
        const req = getRequestInfo(apiRequestId);
        if (!req) return '-';
        return (
          <Space>
            <Tag color={getMethodColor(req.method)}>{req.method}</Tag>
            <span>{req.name}</span>
          </Space>
        );
      },
    },
    {
      title: '类型',
      dataIndex: 'request_type',
      key: 'request_type',
      width: 120,
      render: (value, record, index) => (
        <Select
          value={value}
          onChange={(v) => updateRequestType(index, v)}
          options={REQUEST_TYPE_OPTIONS}
          style={{ width: 100 }}
          size="small"
        />
      ),
    },
    {
      title: '失败即停',
      dataIndex: 'stop_on_failure',
      key: 'stop_on_failure',
      width: 100,
      render: (value, record, index) => (
        <Switch
          checked={value}
          onChange={(checked) => updateStopOnFailure(index, checked)}
          size="small"
        />
      ),
    },
    {
      title: '配置摘要',
      key: 'summary',
      width: 150,
      render: (_, record) => {
        const summary = getSummary(record);
        return summary ? <span style={{ color: '#666', fontSize: 12 }}>{summary}</span> : '-';
      },
    },
    {
      title: '',
      key: 'action',
      width: 60,
      render: (_, record, index) => (
        <DeleteOutlined
          onClick={() => removeRequest(index)}
          style={{ color: '#ff4d4f', cursor: 'pointer' }}
        />
      ),
    },
  ];

  const handleSave = async (values) => {
    const payload = {
      name: values.name,
      description: values.description || '',
      execution_mode: values.execution_mode,
      variables: values.variables || [],
      requests: selectedRequestIds,
      project: 1,
    };

    if (collectionRequests.length > 0) {
      payload.collection_requests = collectionRequests.map((req, index) => ({
        api_request: req.api_request,
        order_index: index,
        request_type: req.request_type || 'normal',
        stop_on_failure: req.stop_on_failure !== false,
        extract_rules: values.execution_mode === 'chain' ? (req.extract_rules || []) : [],
        assertions: values.execution_mode === 'chain' ? (req.assertions || []) : [],
        pre_actions: req.pre_actions || [],
      }));
    }

    onSave(payload, editingRecord);
  };

  return (
    <Modal
      title={editingRecord ? '编辑请求集合' : '创建请求集合'}
      open={visible}
      onCancel={onClose}
      onOk={() => form.submit()}
      width={900}
      okText="保存"
      cancelText="取消"
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleSave}>
        <Form.Item
          name="name"
          label="集合名称"
          rules={[{ required: true, message: '请输入集合名称' }]}
        >
          <Input placeholder="请输入集合名称" />
        </Form.Item>

        <Form.Item name="description" label="描述">
          <Input.TextArea rows={2} placeholder="请输入集合描述（可选）" />
        </Form.Item>

        <Form.Item
          name="execution_mode"
          label="执行模式"
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { label: '链式执行（支持变量传递）', value: 'chain' },
              { label: '并发执行', value: 'concurrent' },
            ]}
          />
        </Form.Item>

        {executionMode === 'chain' && (
          <Form.Item
            name="variables"
            label="场景变量"
            help="变量可在请求中使用 {{变量名}} 引用"
          >
            <VariablesConfig />
          </Form.Item>
        )}

        <Divider />

        <Form.Item label="选择请求" required>
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
            style={{ marginBottom: 12 }}
          />

          {collectionRequests.length > 0 && (
            <Table
              columns={columns}
              dataSource={collectionRequests}
              rowKey="api_request"
              pagination={false}
              size="small"
              expandable={{
                expandedRowRender,
                expandedRowKeys,
                onExpandedRowsChange: setExpandedRowKeys,
                rowExpandable: () => true,
                expandIcon: ({ expanded, onExpand, record }) => (
                  <Space>
                    {expanded ? (
                      <Tag onClick={() => onExpand(record)} style={{ cursor: 'pointer' }}>
                        收起
                      </Tag>
                    ) : (
                      <Tag color="processing" onClick={() => onExpand(record)} style={{ cursor: 'pointer' }}>
                        展开
                      </Tag>
                    )}
                  </Space>
                ),
              }}
            />
          )}
        </Form.Item>

        {executionMode === 'concurrent' && (
          <Alert
            message="并发模式下所有请求同时执行，无顺序依赖，不支持变量提取和断言"
            type="info"
            showIcon
          />
        )}
      </Form>
    </Modal>
  );
};

export default CollectionFormModal;