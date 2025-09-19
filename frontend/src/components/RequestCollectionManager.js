import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
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
  notification 
} from 'antd';

const { Title } = Typography;

function RequestCollectionManager() {
  const [collections, setCollections] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [form] = Form.useForm();

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/request-collections/');
      setCollections(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取请求集合失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRequests = useCallback(async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/api-requests/');
      setRequests(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取API请求列表失败', description: error.message });
    }
  }, []);

  useEffect(() => {
    fetchCollections();
    fetchRequests();
  }, [fetchCollections, fetchRequests]);

  const onFinish = async (values) => {
    try {
      await axios.post('http://localhost:8000/api/request-collections/', {
        ...values,
        project: 1, // 默认项目ID
      });
      notification.success({ message: '集合已保存' });
      fetchCollections();
      form.resetFields();
    } catch (error) {
      notification.error({ message: '创建请求集合失败', description: error.message });
    }
  };

  const handleExecuteCollection = async (collectionId) => {
    setExecuting(true);
    setExecutionResult(null);
    try {
      const response = await axios.post(`http://localhost:8000/api/request-collections/${collectionId}/execute/`);
      setExecutionResult(response.data);
      notification.info({ message: '集合执行完毕' });
      fetchCollections(); // Refresh list to show new status if any
    } catch (error) {
      notification.error({ message: '执行请求集合失败', description: error.message });
    } finally {
      setExecuting(false);
    }
  };

  const collectionColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '请求数量', dataIndex: 'request_count', key: 'request_count', align: 'center' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button onClick={() => handleExecuteCollection(record.id)} loading={executing}>执行</Button>
      ),
    },
  ];

  return (
    <Row gutter={24}>
      <Col span={8}>
        <Title level={3}>创建请求集合</Title>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="name" label="集合名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="requests" label="选择请求" rules={[{ required: true, message: '请至少选择一个API请求' }]}>
            <Select
              mode="multiple"
              allowClear
              placeholder="请选择要包含的API请求"
              options={requests.map(req => ({ label: `${req.name} (${req.method})`, value: req.id }))}
              filterOption={(input, option) => 
                option.label.toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">保存集合</Button>
          </Form.Item>
        </Form>
      </Col>
      <Col span={16}>
        <Title level={3}>已保存的集合</Title>
        <Table columns={collectionColumns} dataSource={collections} loading={loading} rowKey="id" pagination={{ pageSize: 5 }} />
        
        {executionResult && (
          <Card title="执行结果" style={{ marginTop: 24 }} loading={executing}>
             <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="状态">{executionResult.status}</Descriptions.Item>
              <Descriptions.Item label="通过率">{executionResult.pass_rate}%</Descriptions.Item>
              <Descriptions.Item label="通过数">{executionResult.passed_requests}</Descriptions.Item>
              <Descriptions.Item label="失败数">{executionResult.failed_requests}</Descriptions.Item>
            </Descriptions>
            <Title level={5} style={{ marginTop: 16 }}>详细输出</Title>
            <Card style={{ background: '#f0f2f5', maxHeight: 300, overflow: 'auto' }}>
              <pre>{executionResult.output}</pre>
            </Card>
          </Card>
        )}
      </Col>
    </Row>
  );
}

export default RequestCollectionManager;
