import React, { useReducer, useEffect, useCallback, useState } from 'react';
import apiClient from '../api/axios';
import { Table, Button, Upload, Card, Space, Typography, Tag, notification, Descriptions, Modal, Input, Form, Select, Collapse } from 'antd';
import { UploadOutlined, EyeOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { usePermissions } from '../hooks/usePermissions';

const { Title } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const initialState = {
  scripts: [],
  loading: true,
  executingId: null,
  executionResult: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, loading: true };
    case 'FETCH_SUCCESS':
      return { ...state, loading: false, scripts: action.payload };
    case 'FETCH_ERROR':
      return { ...state, loading: false };
    case 'EXECUTE_START':
      return { ...state, executingId: action.payload, executionResult: null };
    case 'EXECUTE_SUCCESS':
      return { ...state, executingId: null, executionResult: action.payload };
    case 'EXECUTE_ERROR':
      return { ...state, executingId: null, executionResult: action.payload };
    default:
      throw new Error();
  }
}

function getScriptTypeTag(scriptType) {
  switch (scriptType) {
    case 'yaml':
      return <Tag color="blue">YAML</Tag>;
    case 'json':
      return <Tag color="green">JSON</Tag>;
    case 'api':
      return <Tag color="purple">API</Tag>;
    case 'python':
      return <Tag color="orange">Python</Tag>;
    case 'selenium':
      return <Tag color="red">Selenium</Tag>;
    default:
      return <Tag>{scriptType}</Tag>;
  }
}

function TestScriptList() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { scripts, loading, executingId, executionResult } = state;
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewScript, setPreviewScript] = useState(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createForm] = Form.useForm();
  const [projectList, setProjectList] = useState([]);
  const [composeContent, setComposeContent] = useState('');
  const { hasCrudPermission } = usePermissions();

  const fetchScripts = useCallback(async () => {
    dispatch({ type: 'FETCH_START' });
    try {
      const response = await apiClient.get('/test-scripts/');
      dispatch({ type: 'FETCH_SUCCESS', payload: response.data.results || [] });
    } catch (error) {
      notification.error({ message: '获取测试脚本失败', description: error.message });
      dispatch({ type: 'FETCH_ERROR' });
    }
  }, []);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  // 获取项目列表
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await apiClient.get('/projects/');
        setProjectList(response.data.results || []);
      } catch (error) {
        notification.error({ message: '获取项目列表失败', description: error.message });
      }
    };
    fetchProjects();
  }, []);

  const handleExecuteScript = async (scriptId) => {
    dispatch({ type: 'EXECUTE_START', payload: scriptId });
    try {
      const response = await apiClient.post(`/test-scripts/${scriptId}/execute/`);
      dispatch({ type: 'EXECUTE_SUCCESS', payload: response.data });
      notification.success({ message: '脚本执行成功' });
      fetchScripts(); // Refresh list to update status
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      dispatch({ type: 'EXECUTE_ERROR', payload: { status: 'error', output: '', error_message: errorMsg } });
      notification.error({ message: '脚本执行失败', description: errorMsg });
    }
  };

  const handlePreview = (script) => {
    setPreviewScript(script);
    setPreviewVisible(true);
  };

  const handleFileUpload = async ({ file, onSuccess, onError }, scriptType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name);
    formData.append('description', `Uploaded on ${new Date().toLocaleDateString()}`);
    formData.append('script_type', scriptType || 'yaml');

    try {
      await apiClient.post('/test-scripts/', formData, {
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

  const handleCreateFromCompose = async () => {
    try {
      const values = await createForm.validateFields();

      const formData = new FormData();
      const blob = new Blob([composeContent], { type: 'text/plain' });
      const file = new File([blob], values.name + (values.format === 'yaml' ? '.yaml' : '.json'));

      formData.append('file', file);
      formData.append('name', values.name);
      formData.append('description', values.description || '');
      formData.append('script_type', values.format);
      formData.append('project', values.project);

      await apiClient.post('/test-scripts/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      notification.success({ message: '创建成功' });
      setCreateModalVisible(false);
      createForm.resetFields();
      setComposeContent('');
      fetchScripts();
    } catch (error) {
      notification.error({ message: '创建失败', description: error.message });
    }
  };

  const columns = [
    { title: '脚本名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'script_type', key: 'script_type', render: (type) => getScriptTypeTag(type) },
    { title: '项目', dataIndex: 'project_name', key: 'project_name' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button onClick={() => handleExecuteScript(record.id)} loading={executingId === record.id}>
            执行
          </Button>
          <Button icon={<EyeOutlined />} onClick={() => handlePreview(record)}>
            预览
          </Button>
        </Space>
      ),
    },
  ];

  const { Panel } = Collapse;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>测试脚本管理</Title>
        <Space>
          <Button onClick={() => setCreateModalVisible(true)} disabled={!hasCrudPermission()}>创建脚本</Button>
          <Upload customRequest={(info) => handleFileUpload(info)} showUploadList={false}>
            <Button icon={<UploadOutlined />} disabled={!hasCrudPermission()}>上传脚本</Button>
          </Upload>
        </Space>
      </div>

      {/* 功能使用说明 */}
      <Card>
        <Collapse>
          <Panel 
            header={
              <Space>
                <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                <strong>测试脚本功能使用说明</strong>
              </Space>
            } 
            key="usage-guide"
          >
            <div style={{ padding: '16px 0' }}>
              <Typography.Paragraph>
                <Title level={4}>📖 功能概述</Title>
                <p>
                  测试脚本是一个<strong>高级功能</strong>，支持通过 YAML/JSON 格式编写复杂的测试链路。
                  它提供了比请求集合更强大的功能，包括 setup/teardown、变量初始化、灵活的断言配置等。
                </p>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>🎯 适用场景</Title>
                <ul>
                  <li>需要复杂测试流程的场景（如登录→创建数据→验证→清理）</li>
                  <li>需要前置准备和后置清理的测试（setup/teardown）</li>
                  <li>需要版本控制和CI/CD集成的测试</li>
                  <li>需要灵活配置和复杂逻辑的测试场景</li>
                </ul>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>📝 脚本格式</Title>
                <p>测试脚本支持 <strong>YAML</strong> 和 <strong>JSON</strong> 两种格式，推荐使用 YAML（更易读）。</p>
                
                <Title level={5}>基本结构：</Title>
                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto' }}>
{`name: 测试名称
description: 测试描述
variables:
  base_url: "https://api.example.com"
  username: "testuser"

setup:
  - name: 登录
    request:
      method: POST
      url: "{{base_url}}/login"
      json:
        username: "{{username}}"
        password: "password123"
    extract:
      - name: token
        jsonpath: "$.data.token"
    assertions:
      - type: status_code
        expected: 200

test_steps:
  - name: 获取用户信息
    request:
      method: GET
      url: "{{base_url}}/user/info"
      headers:
        Authorization: "Bearer {{token}}"
    assertions:
      - type: status_code
        expected: 200
      - type: jsonpath
        expression: "$.code"
        expected: 0

teardown:
  - name: 登出
    request:
      method: POST
      url: "{{base_url}}/logout"
      headers:
        Authorization: "Bearer {{token}}"`}
                </pre>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>🔧 核心功能</Title>
                
                <Title level={5}>1. 变量管理</Title>
                <ul>
                  <li><strong>初始化变量</strong>：在 <code>variables</code> 中定义初始变量</li>
                  <li><strong>变量提取</strong>：使用 <code>extract</code> 从响应中提取变量（JSONPath）</li>
                  <li><strong>模板渲染</strong>：使用 <code>{`{{variable}}`}</code> 在请求中使用变量</li>
                </ul>

                <Title level={5}>2. Setup/Teardown</Title>
                <ul>
                  <li><strong>Setup</strong>：在测试步骤前执行，用于准备测试环境（如登录、创建数据）</li>
                  <li><strong>Teardown</strong>：在测试步骤后执行，无论成功失败都会执行，用于清理（如登出、删除数据）</li>
                  <li>如果 Setup 失败，测试步骤不会执行，但 Teardown 仍会执行</li>
                </ul>

                <Title level={5}>3. 断言验证</Title>
                <ul>
                  <li><strong>状态码断言</strong>：<code>type: status_code, expected: 200</code></li>
                  <li><strong>JSONPath断言</strong>：<code>type: jsonpath, expression: "$.code", expected: 0</code></li>
                  <li>断言失败会导致步骤失败，根据 <code>stop_on_failure</code> 决定是否继续</li>
                </ul>

                <Title level={5}>4. 执行控制</Title>
                <ul>
                  <li><strong>stop_on_failure</strong>：步骤失败时是否停止执行（默认 true）</li>
                  <li>所有步骤按顺序执行，支持变量传递</li>
                </ul>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>💡 使用技巧</Title>
                <ul>
                  <li>使用有意义的步骤名称，便于调试和日志查看</li>
                  <li>合理使用变量，避免硬编码</li>
                  <li>在 Setup 中完成登录等前置操作，提取 token 等认证信息</li>
                  <li>在 Teardown 中清理测试数据，保持环境干净</li>
                  <li>使用 JSONPath 精确提取需要的变量值</li>
                  <li>为关键步骤添加断言，确保测试的可靠性</li>
                </ul>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>🔄 与请求集合的对比</Title>
                <p>
                  <strong>测试脚本</strong>适合复杂场景和版本控制，<strong>请求集合</strong>适合UI管理和快速配置。
                  两者功能相似，但测试脚本提供了更灵活的配置方式和更强大的功能。
                </p>
                <p>
                  <strong>提示</strong>：如果只是简单的顺序执行和变量传递，建议使用请求集合的链式执行模式。
                  只有在需要 setup/teardown、复杂逻辑或版本控制时，才使用测试脚本。
                </p>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>📚 示例脚本</Title>
                <p>完整的示例脚本可以在创建脚本时参考模板，或查看系统提供的示例。</p>
              </Typography.Paragraph>
            </div>
          </Panel>
        </Collapse>
      </Card>

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
          <Title level={5} style={{ marginTop: 16 }}>输出日志</Title>
          <Card style={{ background: '#f5f5f5', maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap' }}>
              {executionResult.output}
            </pre>
          </Card>
        </Card>
      )}

      {/* 脚本预览模态框 */}
      <Modal
        title={`脚本预览 - ${previewScript?.name || ''}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {previewScript && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="名称">{previewScript.name}</Descriptions.Item>
              <Descriptions.Item label="类型">{getScriptTypeTag(previewScript.script_type)}</Descriptions.Item>
              <Descriptions.Item label="项目">{previewScript.project_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(previewScript.created_at).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {previewScript.description || '无描述'}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5} style={{ marginTop: 16, marginBottom: 8 }}>
              脚本内容（预览）
            </Title>
            <Card style={{ background: '#f5f5f5', maxHeight: 400, overflow: 'auto' }}>
              <pre style={{ fontFamily: 'monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap' }}>
                {/* 这里可以显示文件内容，需要后端提供接口 */}
                暂不支持内容预览
              </pre>
            </Card>
          </Space>
        )}
      </Modal>

      {/* 创建脚本模态框 */}
      <Modal
        title="创建测试脚本"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
          setComposeContent('');
        }}
        footer={[
          <Button key="cancel" onClick={() => {
            setCreateModalVisible(false);
            createForm.resetFields();
            setComposeContent('');
          }}>
            取消
          </Button>,
          <Button key="submit" type="primary" onClick={handleCreateFromCompose} disabled={!hasCrudPermission()}>
            创建
          </Button>
        ]}
        width={900}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="name"
            label="脚本名称"
            rules={[{ required: true, message: '请输入脚本名称' }]}
          >
            <Input placeholder="例如：用户下单流程测试" />
          </Form.Item>

          <Form.Item name="description" label="脚本描述">
            <TextArea rows={3} placeholder="描述这个脚本的用途" />
          </Form.Item>

          <Form.Item
            name="format"
            label="脚本格式"
            rules={[{ required: true }]}
            initialValue="yaml"
          >
            <Select>
              <Option value="yaml">YAML</Option>
              <Option value="json">JSON</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="project"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select placeholder="选择项目">
              {projectList.map(project => (
                <Option key={project.id} value={project.id}>{project.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="脚本内容">
            <TextArea
              rows={20}
              placeholder={`输入YAML或JSON格式的测试脚本，例如:\n\nname: 用户下单流程测试\ndescription: 完整用户注册-登录-下单流程\n\nvariables:\n  username: test_user_001\n  password: \"123456\"\n\ntest_steps:\n  - name: 用户注册\n    request:\n      method: POST\n      url: https://api.example.com/register\n      json:\n        username: "{{username}}"\n        password: "{{password}}"\n    extract:\n      - name: user_id\n        jsonpath: "$.data.user_id"`}
              style={{ fontFamily: 'monospace', fontSize: 13 }}
              value={composeContent}
              onChange={(e) => setComposeContent(e.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

export default TestScriptList;
