import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Table, Button, Upload, Card, Space, Typography, Tag, notification, Descriptions } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const { Title } = Typography;

function TestScriptList() {
  const [scripts, setScripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);

  const fetchScripts = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/test-scripts/');
      setScripts(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取测试脚本失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  const handleExecuteScript = async (scriptId) => {
    setExecutingId(scriptId);
    setExecutionResult(null);
    try {
      const response = await axios.post(`http://localhost:8000/api/test-scripts/${scriptId}/execute/`);
      setExecutionResult(response.data);
      notification.success({ message: '脚本执行成功' });
      fetchScripts(); // Refresh list to update status
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      setExecutionResult({ status: 'error', output: '', error_message: errorMsg });
      notification.error({ message: '脚本执行失败', description: errorMsg });
    } finally {
      setExecutingId(null);
    }
  };

  const handleFileUpload = async ({ file, onSuccess, onError }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name);
    formData.append('description', `Uploaded on ${new Date().toLocaleDateString()}` );
    formData.append('script_type', 'python'); // Assuming python, can be dynamic
    formData.append('project', 1); // Default project ID

    try {
      await axios.post('http://localhost:8000/api/test-scripts/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      onSuccess();
      notification.success({ message: `${file.name} 上传成功` });
      fetchScripts();
    } catch (error) {
      onError(error);
      notification.error({ message: `${file.name} 上传失败`, description: error.message });
    }
  };

  const columns = [
    { title: '脚本名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'script_type', key: 'script_type', render: type => <Tag>{type}</Tag> },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button onClick={() => handleExecuteScript(record.id)} loading={executingId === record.id}>
          执行
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>测试脚本管理</Title>
        <Upload customRequest={handleFileUpload} showUploadList={false}>
          <Button icon={<UploadOutlined />}>上传脚本</Button>
        </Upload>
      </div>
      <Table
        columns={columns}
        dataSource={scripts}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />
      {executionResult && (
        <Card title="最近一次执行结果">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="状态">
              <Tag color={executionResult.status === 'success' ? 'green' : 'red'}>
                {executionResult.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="错误信息">{executionResult.error_message || '无'}</Descriptions.Item>
          </Descriptions>
          <Title level={5} style={{ marginTop: 16 }}>输出</Title>
          <Card style={{ background: '#f0f2f5', maxHeight: 300, overflow: 'auto' }}>
            <pre>{executionResult.output}</pre>
          </Card>
        </Card>
      )}
    </Space>
  );
}

export default TestScriptList;
