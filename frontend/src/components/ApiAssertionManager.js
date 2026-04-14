import React, { useState, useEffect, useReducer } from 'react';
import apiClient from '../api/axios';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Table,
  Card,
  Space,
  Tag,
  Row,
  Col,
  notification,
  Popconfirm,
} from 'antd';
import { usePermissions } from '../hooks/usePermissions';

const { Option } = Select;

// API断言管理模块 - 与后端同步执行优化协调
const ApiAssertionManager = ({ 
  visible, 
  onClose, 
  apiRequestId,
  onUpdate = () => {}, 
  title = "API断言管理" 
}) => {
  const [form] = Form.useForm();
  const [data, setData] = useReducer((state, newState) => ({ ...state, ...newState }), {
    assertions: [],
    loading: false,
    saving: false,
  });
  const { assertions, loading, saving } = data;
  const [editingAssertion, setEditingAssertion] = useState(null);
  const { hasCrudPermission } = usePermissions();

  // 获取断言列表
  useEffect(() => {
    if (visible && apiRequestId) {
      fetchAssertions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, apiRequestId]);

  const fetchAssertions = async () => {
    setData({ loading: true });
    try {
      const response = await apiClient.get(`/api-assertions/?api_request=${apiRequestId}`);
      setData({ assertions: response.data.results || [], loading: false });
    } catch (error) {
      notification.error({ message: '获取断言失败', description: error.message });
      setData({ loading: false });
    }
  };

  const handleSubmit = async (values) => {
    setData({ saving: true });
    try {
      if (editingAssertion) {
        // 更新现有断言
        await apiClient.patch(`/api-assertions/${editingAssertion.id}/`, {
          ...values,
          api_request: apiRequestId,
        });
        notification.success({ message: '断言已更新' });
      } else {
        // 创建新断言
        await apiClient.post('/api-assertions/', {
          ...values,
          api_request: apiRequestId,
        });
        notification.success({ message: '断言已添加' });
      }
      form.resetFields();
      setEditingAssertion(null);
      fetchAssertions();
      onUpdate(); // 通知父组件更新
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      notification.error({ 
        message: editingAssertion ? '更新断言失败' : '添加断言失败', 
        description: errorMsg 
      });
    } finally {
      setData({ saving: false });
    }
  };

  const handleDelete = async (assertionId) => {
    try {
      await apiClient.delete(`/api-assertions/${assertionId}/`);
      notification.success({ message: '断言已删除' });
      fetchAssertions();
      onUpdate();
    } catch (error) {
      notification.error({ message: '删除断言失败', description: error.message });
    }
  };

  const handleEdit = (assertion) => {
    setEditingAssertion(assertion);
    form.setFieldsValue({
      assertion_type: assertion.assertion_type,
      field_path: assertion.field_path || '', // 兼容旧字段名field
      comparison: assertion.comparison,
      expected_value: assertion.expected_value,
    });
  };

  // 断言类型中文描述
  const getAssertionTypeName = (type) => {
    const types = {
      status_code: '状态码',
      response_body_field: '响应体字段',
      response_header_field: '响应头字段',
      response_time: '响应时间',
    };
    return types[type] || type;
  };

  // 比较方式中文描述
  const getComparisonName = (comp) => {
    const comparisons = {
      equals: '等于',
      contains: '包含',
      not_contains: '不包含',
      gt: '大于',
      gte: '大于等于',
      lt: '小于',
      lte: '小于等于',
      exists: '存在',
      not_exists: '不存在',
    };
    return comparisons[comp] || comp;
  };

  // 断言表格列定义
  const columns = [
    {
      title: '断言类型',
      dataIndex: 'assertion_type',
      key: 'assertion_type',
      render: (type) => <Tag color="blue">{getAssertionTypeName(type)}</Tag>,
    },
    {
      title: '字段路径',
      dataIndex: 'field_path',
      key: 'field_path',
      render: (path, record) => path || record.field || '-', // 兼容旧字段名field
    },
    {
      title: '比较方式',
      dataIndex: 'comparison', 
      key: 'comparison',
      render: (comparison) => <Tag color="green">{getComparisonName(comparison)}</Tag>,
    },
    {
      title: '期望值',
      dataIndex: 'expected_value',
      key: 'expected_value',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button 
            size="small" 
            onClick={() => handleEdit(record)}
            disabled={!hasCrudPermission()}
          >
            修改
          </Button>
          <Popconfirm
            title="确定删除该断言吗？"
            onConfirm={() => handleDelete(record.id)}
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
    }
  ];

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={1000}
    >
      <Row gutter={24}>
        <Col span={24}>
          {/* 添加/编辑断言表单 */}
          <Card 
            title={editingAssertion ? "修改断言" : "添加断言"} 
            size="small" 
            style={{ marginBottom: 24 }}
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{ comparison: 'equals', field_path: '' }}
            >
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item 
                    name="assertion_type" 
                    label="断言类型"
                    rules={[{ required: true, message: '请选择断言类型' }]}
                  >
                    <Select placeholder="选择断言类型">
                      <Option value="status_code">状态码</Option>
                      <Option value="response_body_field">响应体字段</Option>
                      <Option value="response_header_field">响应头字段</Option>
                      <Option value="response_time">响应时间</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col span={6}>
                  <Form.Item 
                    name="comparison" 
                    label="比较方式"
                    rules={[{ required: true, message: '请选择比较方式' }]}
                  >
                    <Select placeholder="选择比较方式">
                      <Option value="equals">等于</Option>
                      <Option value="contains">包含</Option>
                      <Option value="not_contains">不包含</Option>
                      <Option value="gt">大于</Option>
                      <Option value="gte">大于等于</Option>
                      <Option value="lt">小于</Option>
                      <Option value="lte">小于等于</Option>
                      <Option value="exists">存在</Option>
                      <Option value="not_exists">不存在</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col span={12}>
                  <Form.Item 
                    name="expected_value" 
                    label="期望值"
                    rules={[{ required: true, message: '请输入期望值' }]}
                  >
                    <Input 
                      placeholder="输入期望值（如：200、success、true）" 
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item
                noStyle
                shouldUpdate={(prev, curr) => prev.assertion_type !== curr.assertion_type}
              >
                {({ getFieldValue }) => {
                  const assertionType = getFieldValue('assertion_type');
                  const needsFieldPath = assertionType === 'response_body_field' || assertionType === 'response_header_field';
                  
                  return needsFieldPath ? (
                    <Form.Item
                      name="field_path"
                      label="字段路径"
                      rules={[
                        { 
                          required: true, 
                          message: '请指定字段路径' 
                        },
                        { 
                          pattern: /^[a-zA-Z0-9_.\-[\]]*$/,  // 简单的正则校验，确保路径合理
                          message: '有效的JSON路径，如data.id, $.data.id, result.items[0]'
                        }
                      ]}
                    >
                      <Input 
                        placeholder={
                          assertionType === 'response_body_field' 
                            ? '如: data.id 或 $.data.id 或 result.items[0]' 
                            : '响应头字段名，如: Content-Type'
                        }
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  ) : null;
                }}
              </Form.Item>
              
              <Form.Item>
                <Space>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={saving}
                  >
                    {editingAssertion ? '更新断言' : '添加断言'}
                  </Button>
                  {editingAssertion && (
                    <Button onClick={() => {
                      form.resetFields();
                      setEditingAssertion(null);
                    }}>
                      取消
                    </Button>
                  )}
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {/* 断言列表 */}
          <Card title={`断言列表 (${assertions.length})`} size="small">
            <Table
              dataSource={assertions}
              columns={columns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10, showSizeChanger: true }}
            />
          </Card>
        </Col>
      </Row>
    </Modal>
  );
};

export default ApiAssertionManager;