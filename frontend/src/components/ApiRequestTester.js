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
  Tag,
  notification
} from 'antd';

const { Title } = Typography;
const { Option } = Select;

function ApiRequestTester() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [form] = Form.useForm();

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/api-requests/');
      setRequests(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取API请求失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const onFinish = async (values) => {
    try {
      let headers = {};
      if (values.headers) {
        values.headers.split('\n').forEach(line => {
          const [key, value] = line.split(':').map(str => str.trim());
          if (key && value) {
            headers[key] = value;
          }
        });
      }
      
      await axios.post('http://localhost:8000/api/api-requests/', {
        ...values,
        headers: JSON.stringify(headers),
        project: 1, // 默认项目ID
      });
      notification.success({ message: '请求已保存' });
      fetchRequests();
      form.resetFields();
    } catch (error) {
      notification.error({ message: '创建API请求失败', description: error.message });
    }
  };

  const handleTestRequest = async (requestId) => {
    setTesting(true);
    setTestResult(null);
    try {
      const response = await axios.post(`http://localhost:8000/api/api-requests/${requestId}/execute/`);
      setTestResult(response.data);
      notification.info({ message: '测试完成' });
    } catch (error) {
      notification.error({ message: '测试API请求失败', description: error.message });
    } finally {
      setTesting(false);
    }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: 'URL', dataIndex: 'url', key: 'url' },
    { title: '方法', dataIndex: 'method', key: 'method', render: method => <Tag color="blue">{method}</Tag> },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button onClick={() => handleTestRequest(record.id)} loading={testing}>测试</Button>
      ),
    },
  ];

  return (
    <Row gutter={24}>
      <Col span={8}>
        <Title level={3}>创建API请求</Title>
        <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ method: 'GET' }}>
          <Form.Item name="name" label="请求名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="url" label="URL" rules={[{ required: true, type: 'url' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="method" label="方法" rules={[{ required: true }]}>
            <Select>
              <Option value="GET">GET</Option>
              <Option value="POST">POST</Option>
              <Option value="PUT">PUT</Option>
              <Option value="PATCH">PATCH</Option>
              <Option value="DELETE">DELETE</Option>
            </Select>
          </Form.Item>
          <Form.Item name="headers" label="请求头">
            <Input.TextArea rows={4} placeholder="Content-Type: application/json\nAuthorization: Bearer token" />
          </Form.Item>
          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">保存请求</Button>
          </Form.Item>
        </Form>
      </Col>
      <Col span={16}>
        <Title level={3}>已保存的请求</Title>
        <Table columns={columns} dataSource={requests} loading={loading} rowKey="id" pagination={{ pageSize: 5 }} />
        
        {testResult && (
          <Card title="测试结果" style={{ marginTop: 24 }} loading={testing}>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="状态码">
                <Tag color={testResult.status_code >= 200 && testResult.status_code < 300 ? 'green' : 'red'}>
                  {testResult.status_code}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="响应时间">{testResult.response_time.toFixed(4)} 秒</Descriptions.Item>
            </Descriptions>
            <Title level={5} style={{ marginTop: 16 }}>断言结果</Title>
            {(testResult.assertions && testResult.assertions.length > 0) ? (
              <Table
                size="small"
                pagination={false}
                dataSource={testResult.assertions}
                columns={[
                  { title: '断言', dataIndex: 'assertion', key: 'assertion' },
                  {
                    title: '结果',
                    dataIndex: 'passed',
                    key: 'passed',
                    render: passed => passed ? <Tag color="success">通过</Tag> : <Tag color="error">失败</Tag>
                  }
                ]}
                rowKey={(r, i) => i}
              />
            ) : <p>无断言</p>}
            <Title level={5} style={{ marginTop: 16 }}>响应内容</Title>
            <Card style={{ background: '#f0f2f5'}}>
              <pre style={{ maxHeight: 200, overflow: 'auto' }}>{JSON.stringify(JSON.parse(testResult.response_body), null, 2)}</pre>
            </Card>
          </Card>
        )}
      </Col>
    </Row>
  );
}

export default ApiRequestTester;
