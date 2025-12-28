import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/axios';
import { Table, Input, Button, Space, Typography, Tag, notification, Modal, Form, Select } from 'antd';

const { Title } = Typography;

function TestCaseList({ projectId }) { // Accept projectId as a prop
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  // Local filter state, only used when projectId is not provided
  const [filter, setFilter] = useState({ project: '', module: '' });
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  const fetchTestCases = useCallback(async (searchFilter = null) => {
    setLoading(true);
    try {
      // 使用传入的searchFilter，如果没有则使用空filter（用于初始加载，显示所有数据）
      const currentFilter = searchFilter !== null ? searchFilter : { project: '', module: '' };
      
      // 构建测试用例查询参数
      let testcaseUrl = '/testcases/';
      const testcaseParams = new URLSearchParams();
      
      if (projectId) {
        testcaseParams.append('project', projectId);
      } else {
        if (currentFilter.project) testcaseParams.append('project__name__icontains', currentFilter.project);
        if (currentFilter.module) testcaseParams.append('module__name__icontains', currentFilter.module);
      }
      
      const testcaseQueryString = testcaseParams.toString();
      if (testcaseQueryString) {
        testcaseUrl += `?${testcaseQueryString}`;
      }

      // 构建API请求查询参数
      let apiRequestUrl = '/api-requests/';
      const apiRequestParams = new URLSearchParams();
      
      if (projectId) {
        apiRequestParams.append('project', projectId);
      }
      
      const apiRequestQueryString = apiRequestParams.toString();
      if (apiRequestQueryString) {
        apiRequestUrl += `?${apiRequestQueryString}`;
      }

      // 同时获取测试用例和API请求数据
      const [testcasesRes, apiRequestsRes] = await Promise.all([
        apiClient.get(testcaseUrl),
        apiClient.get(apiRequestUrl)
      ]);

      // 获取数据
      const testcases = testcasesRes.data.results || [];
      const apiRequests = apiRequestsRes.data.results || [];

      // 将API请求转换为与测试用例类似的格式，并添加类型标识
      const formattedApiRequests = apiRequests.map(apiReq => ({
        ...apiReq,
        title: apiReq.name, // API请求使用name作为title
        module_name: 'API测试', // API请求没有模块，显示为API测试
        priority: null, // API请求没有优先级
        test_type: 'api', // 标识为API测试用例
      }));

      // 将测试用例添加类型标识
      const formattedTestCases = testcases.map(tc => ({
        ...tc,
        test_type: 'testcase', // 标识为传统测试用例
      }));

      // 合并数据并按创建时间倒序排列
      const allTestCases = [...formattedTestCases, ...formattedApiRequests].sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
      });

      setTestCases(allTestCases);
    } catch (error) {
      notification.error({ message: '获取测试用例失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [projectId]); // 只依赖projectId，不依赖filter

  // 只在初始加载时调用，或者projectId改变时调用
  useEffect(() => {
    fetchTestCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]); // 只在projectId改变时重新加载，不依赖fetchTestCases

  // 获取项目列表
  useEffect(() => {
    const fetchProjects = async () => {
      setProjectsLoading(true);
      try {
        const response = await apiClient.get('/projects/');
        setProjects(response.data.results || []);
      } catch (error) {
        notification.error({ message: '获取项目列表失败', description: error.message });
      } finally {
        setProjectsLoading(false);
      }
    };
    fetchProjects();
  }, []);

  const handleFilterChange = (e) => {
    // 只更新filter状态，不触发请求
    setFilter({ ...filter, [e.target.name]: e.target.value });
  };

  const handleSearch = () => {
    // 点击搜索按钮时才发起请求，使用当前的filter值
    fetchTestCases(filter);
  };

  const openCreateApiTestModal = () => {
    form.resetFields();
    // If we're in a project context, pre-select that project
    if (projectId) {
      form.setFieldsValue({ project: projectId });
    }
    setModalOpen(true);
  };

  const handleCreateApiTest = async () => {
    try {
      const values = await form.validateFields();

      // 处理headers，转换为JSON字符串
      let headers = {};
      if (values.headers) {
        values.headers.split('\n').forEach(line => {
          const [key, value] = line.split(':').map(str => str.trim());
          if (key && value) {
            headers[key] = value;
          }
        });
      }

      await apiClient.post('/api-requests/', {
        name: values.name,
        url: values.url,
        method: values.method,
        headers: JSON.stringify(headers), // 转换为JSON字符串
        body: values.body || '',
        project: values.project, // 使用选中的项目ID
      });
      notification.success({ message: 'API测试用例创建成功' });
      setModalOpen(false);
      form.resetFields();
      // 刷新列表以显示新创建的API测试用例（使用当前的filter）
      fetchTestCases(filter);
    } catch (error) {
      console.error('创建API测试用例失败:', error);
      if (error.response) {
        notification.error({
          message: '创建失败',
          description: error.response.data?.detail || error.response.statusText
        });
      } else if (error.message) {
        notification.error({ message: '创建失败', description: error.message });
      }
    }
  };

  const columns = [
    {
      title: '类型',
      dataIndex: 'test_type',
      key: 'test_type',
      width: 100,
      render: (type) => {
        if (type === 'api') {
          return <Tag color="blue">API测试</Tag>;
        }
        return <Tag color="green">功能测试</Tag>;
      },
    },
    { title: '标题', dataIndex: 'title', key: 'title', render: (text) => <strong>{text}</strong> },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '模块', dataIndex: 'module_name', key: 'module_name' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!projectId && <Title level={2}>测试用例列表</Title>} 
      
      {!projectId && (
        <Space>
          <Input
            placeholder="按项目名称搜索"
            name="project"
            value={filter.project}
            onChange={handleFilterChange}
            style={{ width: 200 }}
          />
          <Input
            placeholder="按模块名称搜索"
            name="module"
            value={filter.module}
            onChange={handleFilterChange}
            style={{ width: 200 }}
          />
          <Button onClick={handleSearch} type="primary">
            搜索
          </Button>
          <Button onClick={openCreateApiTestModal} type="dashed" style={{ marginLeft: 16 }}>
            添加API测试用例
          </Button>
        </Space>
      )}

      <Table
        columns={columns}
        dataSource={testCases}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10, showSizeChanger: true }}
      />

      <Modal
        title="添加API测试用例"
        open={modalOpen}
        onOk={handleCreateApiTest}
        onCancel={() => setModalOpen(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="project"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select
              placeholder="请选择项目"
              loading={projectsLoading}
              disabled={projectsLoading || !!projectId}
            >
              {projects.map(project => (
                <Select.Option key={project.id} value={project.id}>
                  {project.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="name" label="请求名称" rules={[{ required: true, message: '请输入请求名称' }]}>
            <Input />
          </Form.Item>

          <Form.Item name="url" label="URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="https://api.example.com/endpoint" />
          </Form.Item>

          <Form.Item
            name="method"
            label="请求方法"
            rules={[{ required: true, message: '请选择请求方法' }]}
            initialValue="GET"
          >
            <Select>
              <Select.Option value="GET">GET</Select.Option>
              <Select.Option value="POST">POST</Select.Option>
              <Select.Option value="PUT">PUT</Select.Option>
              <Select.Option value="PATCH">PATCH</Select.Option>
              <Select.Option value="DELETE">DELETE</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="headers" label="请求头">
            <Input.TextArea rows={4} placeholder={'Content-Type: application/json\nAuthorization: Bearer token'} />
          </Form.Item>

          <Form.Item name="body" label="请求体">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

export default TestCaseList;