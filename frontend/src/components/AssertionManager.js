import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Button,
  Table,
  Space,
  Tag,
  notification,
  Row,
  Col,
} from 'antd';
import apiClient from '../api/axios';

const { Option } = Select;

// API断言管理组件 - 与同步改进的后端API配合
const AssertionManager = ({ 
  visible, 
  onCancel, 
  apiRequestId, 
  title = 'API断言管理',
  refreshAssertions = () => {}
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [assertions, setAssertions] = useState([]);
  const [editMode, setEditMode] = useState(false);
  const [editingAssertion, setEditingAssertion] = useState(null);

  // 获取API请求的断言列表
  const fetchAssertions = async () => {
    if (!apiRequestId) return;
    
    setLoading(true);
    try {
      const response = await apiClient.get(`/api-assertions/?api_request=${apiRequestId}`);
      setAssertions(response.data.results || []);
    } catch (error) {
      notification.error({ 
        message: '获取断言失败', 
        description: error.message 
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible && apiRequestId) {
      fetchAssertions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, apiRequestId]);

  // 断言表格列定义
  const assertionColumns = [
    {
      title: '断言类型',
      dataIndex: 'assertion_type',
      key: 'assertion_type',
      render: (type) => {
        const typeMap = {
          status_code: '状态码',
          response_time: '响应时间',
          response_body_field: '响应体字段',
          response_header_field: '响应头字段',
        };
        return <Tag color="blue">{typeMap[type] || type}</Tag>;
      },
    },
    {
      title: '字段路径',
      dataIndex: 'field_path',
      key: 'field_path',
      render: (path, record) => path || record.field || '-', // 兼容旧字段名 field
    },
    {
      title: '比较方式', 
      dataIndex: 'comparison',
      key: 'comparison',
      render: (comp) => {
        const compMap = {
          equals: '等于',
          contains: '包含',
          not_contains: '不包含',
          gt: '>', 
          gte: '>=',
          lt: '<',
          lte: '<=',
        };
        return compMap[comp] || comp;
      },
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
        <Space size="small">
          <Button 
            size="small" 
            onClick={() => handleEdit(record)}
          >
            修改
          </Button>
          <Button 
            size="small" 
            danger 
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    }
  ];

  // 处理添加/更新断言
  const handleSubmit = async (values) => {
    try {
      if (!apiRequestId) {
        notification.error({ message: '缺少API请求ID' });
        return;
      }

      if (editMode && editingAssertion) {
        // 更新现有断言
        await apiClient.patch(`/api-assertions/${editingAssertion.id}/`, {
          ...values,
          api_request: apiRequestId
        });
        
        notification.success({ message: '断言更新成功' });
        setEditMode(false);
        setEditingAssertion(null);
      } else {
        // 添加新断言
        await apiClient.post('/api-assertions/', {
          ...values,
          api_request: apiRequestId
        });
        
        notification.success({ message: '断言添加成功' });
      }
      
      form.resetFields();
      await fetchAssertions(); // 刷新列表
      refreshAssertions(); // 通知父组件更新
    } catch (error) {
      notification.error({
        message: editMode ? '更新断言失败' : '添加断言失败',
        description: error.response?.data?.detail || error.message
      });
    }
  };

  // 处理编辑断言
  const handleEdit = (assertion) => {
    setEditingAssertion(assertion);
    setEditMode(true);
    form.setFieldsValue({
      assertion_type: assertion.assertion_type,
      field_path: assertion.field_path || assertion.field || '',  // 兼容旧字段名
      comparison: assertion.comparison,
      expected_value: assertion.expected_value,
    });
  };

  // 处理删除断言
  const handleDelete = async (assertionId) => {
    try {
      await apiClient.delete(`/api-assertions/${assertionId}/`);
      notification.success({ message: '断言删除成功' });
      
      // 刷新列表
      await fetchAssertions();
      refreshAssertions(); // 通知父组件更新
    } catch (error) {
      notification.error({ 
        message: '删除断言失败', 
        description: error.message 
      });
    }
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditMode(false);
    setEditingAssertion(null);
    form.resetFields();
  };

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={1000}
    >
      {/* 断言添加/编辑表单 */}
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
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
              noStyle
              shouldUpdate={(prev, curr) => prev.assertion_type !== curr.assertion_type}
            >
              {({ getFieldValue }) => {
                const assertionType = getFieldValue('assertion_type');
                const needsFieldPath = assertionType === 'response_body_field' || assertionType === 'response_header_field';

                return (
                  <Form.Item
                    name="field_path"
                    label={needsFieldPath ? "字段路径*" : "字段路径"}
                    rules={[
                      { required: needsFieldPath, message: '字段路径为必填项' }
                    ]}
                  >
                    <Input 
                      placeholder={
                        assertionType === 'response_body_field' 
                          ? '如: data.id 或 $.data.id' 
                          : assertionType === 'response_header_field'
                          ? '如: Content-Type'
                          : '可选字段路径'
                      }
                      disabled={!needsFieldPath}
                    />
                  </Form.Item>
                );
              }}
            </Form.Item>
          </Col>

          <Col span={6}>
            <Form.Item name="comparison" label="比较方式" rules={[{ required: true, message: '请选择比较方式' }]}>
              <Select placeholder="选择比较方式">
                <Option value="equals">等于</Option>
                <Option value="contains">包含</Option>
                <Option value="not_contains">不包含</Option>
                <Option value="gt">&gt;</Option>
                <Option value="gte">&gt;=</Option>
                <Option value="lt">&lt;</Option>
                <Option value="lte">&lt;=</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={6}>
            <Form.Item name="expected_value" label="期望值" rules={[{ required: true, message: '请输入期望值' }]}>
              <Input placeholder="输入期望值" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              {editMode ? '更新断言' : '添加断言'}
            </Button>
            {editMode && (
              <Button onClick={handleCancelEdit}>
                取消
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>

      <div style={{ height: 16 }} />

      {/* 断言列表 */}
      <div>
        <h4>当前断言 ({assertions.length} 个)</h4>
        <Table
          dataSource={assertions}
          columns={assertionColumns}
          rowKey="id"
          pagination={{ 
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true
          }}
          loading={loading}
          size="small"
        />
      </div>
    </Modal>
  );
};

export default AssertionManager;