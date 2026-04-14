import React, { useReducer, useEffect, useCallback, useState } from 'react';
import apiClient from '../api/axios';
import { Table, Button, Upload, Card, Space, Typography, Tag, notification, Descriptions, Modal, Input, Form, Select, Collapse, Tabs, Divider } from 'antd';
import { UploadOutlined, EditOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { usePermissions } from '../hooks/usePermissions';
import VariablesConfigurator from './VariablesConfigurator';
import StepConfigurator from './StepConfigurator';

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
  const [editForm] = Form.useForm();
  const [editVisualFormData, setEditVisualFormData] = useState({
    variables: {},
    setup: [],
    test_steps: [],
    teardown: []
  });
  const [editComposeContent, setEditComposeContent] = useState('');
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createForm] = Form.useForm();
  const [projectList, setProjectList] = useState([]);
  const [composeContent, setComposeContent] = useState('');
  const [visualFormData, setVisualFormData] = useState({
    name: '',
    description: '',
    script_type: 'yaml',
    project: '',
    variables: {},
    setup: [],
    test_steps: [],
    teardown: []
  });
  const { hasCrudPermission } = usePermissions();
  const [uploadProjectModalVisible, setUploadProjectModalVisible] = useState(false);
  const [uploadProjectForm] = Form.useForm();
  const [pendingUploadFile, setPendingUploadFile] = useState(null);
  const [pendingScriptType, setPendingScriptType] = useState('yaml');

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
    editForm.setFieldsValue({
      name: script.name,
      description: script.description,
      project: script.project,
    });
    
    try {
      const content = script.content;
      let parsed = {};
      if (script.script_type === 'yaml') {
        const yamlLines = content.split('\n');
        const jsonContent = yamlLines.map(line => {
          if (line.includes(':') && !line.startsWith(' ') && !line.startsWith('#')) {
            const [key, value] = line.split(':');
            return `"${key.trim()}": ${value.trim() || 'null'}`;
          }
          return line;
        }).join('\n');
        parsed = JSON.parse(`{${jsonContent}}`);
      } else {
        parsed = JSON.parse(content);
      }
      
      setEditVisualFormData({
        variables: parsed.variables || {},
        setup: parsed.setup || [],
        test_steps: parsed.test_steps || [],
        teardown: parsed.teardown || [],
      });
      setEditComposeContent(content);
    } catch (e) {
      setEditComposeContent(script.content || '');
      setEditVisualFormData({
        variables: {},
        setup: [],
        test_steps: [],
        teardown: [],
      });
    }
    
    setPreviewVisible(true);
  };

  const handleSaveEdit = async () => {
    try {
      const values = await editForm.validateFields();
      let scriptContent;
      
      if (!editComposeContent) {
        const scriptObj = {
          name: values.name,
          description: values.description,
          variables: editVisualFormData.variables,
        };
        if (editVisualFormData.setup?.length) scriptObj.setup = editVisualFormData.setup;
        if (editVisualFormData.test_steps?.length) scriptObj.test_steps = editVisualFormData.test_steps;
        if (editVisualFormData.teardown?.length) scriptObj.teardown = editVisualFormData.teardown;
        scriptContent = JSON.stringify(scriptObj, null, 2);
      } else {
        scriptContent = editComposeContent;
      }
      
      await apiClient.patch(`/test-scripts/${previewScript.id}/`, {
        name: values.name,
        description: values.description || '',
        content: scriptContent,
        project: values.project,
      });
      
      notification.success({ message: '保存成功' });
      setPreviewVisible(false);
      fetchScripts();
    } catch (error) {
      notification.error({ message: '保存失败', description: error.response?.data?.detail || error.message });
    }
  };

  const updateEditVisualFormField = (field, value) => {
    setEditVisualFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleFileUpload = async ({ file, onSuccess }, scriptType) => {
    const fileName = file.name.replace(/\.[^.]+$/, '');
    uploadProjectForm.setFieldsValue({ name: fileName });
    setPendingUploadFile(file);
    setPendingScriptType(scriptType || 'yaml');
    setUploadProjectModalVisible(true);
    onSuccess();
  };

  const confirmUpload = async () => {
    try {
      const values = await uploadProjectForm.validateFields();
      const content = await pendingUploadFile.text();
      
      await apiClient.post('/test-scripts/', {
        name: values.name,
        description: `Uploaded on ${new Date().toLocaleDateString()}`,
        script_type: pendingScriptType,
        content: content,
        project: values.project,
      });
      
      setUploadProjectModalVisible(false);
      setPendingUploadFile(null);
      uploadProjectForm.resetFields();
      notification.success({ message: `${pendingUploadFile.name} 上传成功` });
      fetchScripts();
    } catch (error) {
      notification.error({ message: '上传失败', description: error.response?.data?.detail || error.message });
    }
  };

  const handleCreateFromCompose = async () => {
    try {
      // 从表单项或可视化编辑器获取数据
      let scriptContent;
      if (!composeContent) {
        // 如果没有直接在代码编辑器中输入内容，从可视化表单生成YAML
        const scriptObj = {
          name: visualFormData.name,
          description: visualFormData.description,
          variables: visualFormData.variables,
        };

        if (visualFormData.setup && visualFormData.setup.length > 0) {
          scriptObj.setup = visualFormData.setup;
        }

        if (visualFormData.test_steps && visualFormData.test_steps.length > 0) {
          scriptObj.test_steps = visualFormData.test_steps;
        }

        if (visualFormData.teardown && visualFormData.teardown.length > 0) {
          scriptObj.teardown = visualFormData.teardown;
        }

        scriptContent = JSON.stringify(scriptObj, null, 2);
      } else {
        scriptContent = composeContent;
      }

      const values = await createForm.validateFields();

      await apiClient.post('/test-scripts/', {
        name: values.name,
        description: values.description || '',
        script_type: 'yaml',
        content: scriptContent,
        project: values.project,
      });

      notification.success({ message: '创建成功' });
      setCreateModalVisible(false);
      createForm.resetFields();
      setComposeContent('');
      setVisualFormData({
        name: '',
        description: '',
        script_type: 'yaml',
        project: '',
        variables: {},
        setup: [],
        test_steps: [],
        teardown: []
      });
      fetchScripts();
    } catch (error) {
      notification.error({ message: '创建失败', description: error.message });
    }
  };

  // 更新可视化表单数据的函数
  const updateVisualFormField = (field, value) => {
    setVisualFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // 将当前可视化表单数据转换为YAML并显示在代码编辑器中
  const convertToYaml = () => {
    const scriptObj = {
      name: visualFormData.name,
      description: visualFormData.description,
      variables: visualFormData.variables,
    };

    if (visualFormData.setup && visualFormData.setup.length > 0) {
      scriptObj.setup = visualFormData.setup;
    }

    if (visualFormData.test_steps && visualFormData.test_steps.length > 0) {
      scriptObj.test_steps = visualFormData.test_steps;
    }

    if (visualFormData.teardown && visualFormData.teardown.length > 0) {
      scriptObj.teardown = visualFormData.teardown;
    }

    setComposeContent(JSON.stringify(scriptObj, null, 2));
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
          <Button icon={<EditOutlined />} onClick={() => handlePreview(record)}>
            编辑
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
              <Tag color={executionResult.success ? 'green' : 'red'}>
                {executionResult.success ? '通过' : '失败'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="错误信息">{executionResult.error || '无'}</Descriptions.Item>
          </Descriptions>
          <Title level={5} style={{ marginTop: 16 }}>输出日志</Title>
          <Card style={{ background: '#f5f5f5', maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap' }}>
              {executionResult.logs ? (Array.isArray(executionResult.logs) ? executionResult.logs.join('\n') : executionResult.logs) : executionResult.output || '无日志'}
            </pre>
          </Card>
        </Card>
      )}

      {/* 脚本编辑模态框 */}
      <Modal
        title={`编辑脚本 - ${previewScript?.name || ''}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setPreviewVisible(false)}>
            取消
          </Button>,
          <Button key="save" type="primary" onClick={handleSaveEdit} disabled={!hasCrudPermission()}>
            保存
          </Button>
        ]}
        width={900}
      >
        {previewScript && (
          <Form form={editForm} layout="vertical">
            <Form.Item
              name="name"
              label="脚本名称"
              rules={[{ required: true, message: '请输入脚本名称' }]}
            >
              <Input />
            </Form.Item>

            <Form.Item name="description" label="脚本描述">
              <TextArea rows={2} />
            </Form.Item>

            <Form.Item
              name="project"
              label="所属项目"
              rules={[{ required: true, message: '请选择项目' }]}
            >
              <Select placeholder="选择项目">
                {projectList.map(p => (
                  <Option key={p.id} value={p.id}>{p.name}</Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item label="脚本内容">
              <Tabs defaultActiveKey="visual">
                <Tabs.TabPane tab="可视化编辑器" key="visual">
                  <Card>
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>变量配置</Divider>
                    <VariablesConfigurator 
                      variables={editVisualFormData.variables} 
                      onChange={(val) => updateEditVisualFormField('variables', val)} 
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>Setup 阶段</Divider>
                    <StepConfigurator 
                      steps={editVisualFormData.setup || []}
                      onChange={(steps) => updateEditVisualFormField('setup', steps)}
                      title="前置准备步骤 (Setup)"
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>测试执行步骤</Divider>
                    <StepConfigurator 
                      steps={editVisualFormData.test_steps || []}
                      onChange={(steps) => updateEditVisualFormField('test_steps', steps)}
                      title="主测试步骤"
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>Teardown 阶段</Divider>
                    <StepConfigurator 
                      steps={editVisualFormData.teardown || []}
                      onChange={(steps) => updateEditVisualFormField('teardown', steps)}
                      title="清理步骤 (Teardown)"
                    />
                  </Card>
                </Tabs.TabPane>
                <Tabs.TabPane tab="代码编辑器" key="code">
                  <TextArea
                    rows={20}
                    style={{ fontFamily: 'monospace', fontSize: 13 }}
                    value={editComposeContent}
                    onChange={(e) => setEditComposeContent(e.target.value)}
                  />
                </Tabs.TabPane>
              </Tabs>
            </Form.Item>
          </Form>
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
            <Tabs defaultActiveKey="visual">
              <Tabs.TabPane tab="可视化编辑器" key="visual">
                <Card>
                  <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>变量配置</Divider>
                    <VariablesConfigurator 
                      variables={visualFormData.variables} 
                      onChange={(val) => updateVisualFormField('variables', val)} 
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>Setup 阶段</Divider>
                    <StepConfigurator 
                      steps={visualFormData.setup || []}
                      onChange={(steps) => updateVisualFormField('setup', steps)}
                      title="前置准备步骤 (Setup)"
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>测试执行步骤</Divider>
                    <StepConfigurator 
                      steps={visualFormData.test_steps || []}
                      onChange={(steps) => updateVisualFormField('test_steps', steps)}
                      title="主测试步骤"
                    />
                    
                    <Divider style={{ background: '#e6f7ff', fontWeight: 600 }}>Teardown 阶段</Divider>
                    <StepConfigurator 
                      steps={visualFormData.teardown || []}
                      onChange={(steps) => updateVisualFormField('teardown', steps)}
                      title="清理步骤 (Teardown)"
                    />
                    
                    <div style={{ marginTop: 16, textAlign: 'center' }}>
                      <Button 
                        type="primary" 
                        onClick={convertToYaml}
                        style={{ marginRight: 8 }}
                      >
                        生成代码预览
                      </Button>
                      <Button 
                        onClick={() => {
                          const sampleData = {
                            name: "OneSimpleWay API测试",
                            description: "登录并查询项目列表",
                            variables: {
                              initial_token: "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NzQ4MzQ1MTUsInN1YiI6IjU5NiIsImV4cCI6MTc4MTMxNDUxNSwidXNlcklkIjoiNTk2IiwidHlwZSI6Imluc3RhbGxlciIsImpvaW5GcmVlTGVhZHNGbGFnIjoxLCJlbWFpbCI6Impvd2V3ODU2NDBAaW51cHVwLmNvbSIsImxvZ2luSWRlbnRpZnkiOiJvdXRlcl9zZWxmIiwiY291bnRyeUNvZGUiOiJBVSJ9.TIlIJizbw2mQ0ud4JAC1ExNKZb77ZbdvLRcYq6cO-J4",
                              accept_language: "en-AU",
                              country_code: "AU"
                            },
                            setup: [
                              {
                                id: "setup-login",
                                name: "用户登录",
                                request: {
                                  method: "POST",
                                  url: "https://au-api.onesimpleway.com/auth/user/login",
                                  headers: {
                                    Authorization: "{{initial_token}}",
                                    "Accept-Language": "{{accept_language}}",
                                    "current-country-code": "{{country_code}}",
                                    "Content-Type": "application/json"
                                  },
                                  json: {
                                    email: "bovime7960@kwifa.com",
                                    password: "hyanjun546",
                                    currentCountryCode: "AU",
                                    currentCountryName: "Australia"
                                  }
                                },
                                extract: [
                                  {
                                    name: "auth_token",
                                    jsonpath: "$.data.token"
                                  }
                                ],
                                assertions: [
                                  {
                                    type: "jsonpath",
                                    expression: "$.code",
                                    expected: 200
                                  }
                                ]
                              }
                            ],
                            test_steps: [
                              {
                                id: "test-qry",
                                name: "查询项目列表",
                                request: {
                                  method: "GET",
                                  url: "https://au-api.onesimpleway.com/sketch/projects/qryList?pageNum=1&pageSize=20&total&companyId&type&status&time&sortFiled=signed_date&sortBy=desc&keyword",
                                  headers: {
                                    Authorization: "{{auth_token}}",
                                    "Accept-Language": "{{accept_language}}",
                                    "current-country-code": "{{country_code}}"
                                  }
                                },
                                assertions: [
                                  {
                                    type: "jsonpath",
                                    expression: "$.code",
                                    expected: 200
                                  }
                                ]
                              }
                            ]
                          };
                          setVisualFormData(sampleData);
                        }}
                      >
                        填充示例数据
                      </Button>
                    </div>
                  </Card>
                </Tabs.TabPane>
              <Tabs.TabPane tab="代码编辑器" key="code">
                <TextArea
                  rows={20}
                  placeholder={'在此处输入YAML或JSON格式的测试脚本，例如:\n\nname: 用户下单流程测试\ndescription: 完整用户注册-登录-下单流程\n\nvariables:\n  username: test_user_001\n  password: 123456\n\ntest_steps:\n  - name: 用户注册\n    request:\n      method: POST\n      url: https://api.example.com/register\n      json:\n        username: {{username}}\n        password: {{password}}\n    extract:\n      - name: user_id\n        jsonpath: $.data.user_id\n    assertions:\n      - type: status_code\n        expected: 200'}
                  style={{ fontFamily: 'monospace', fontSize: 13 }}
                  value={composeContent}
                  onChange={(e) => setComposeContent(e.target.value)}
                />
              </Tabs.TabPane>
            </Tabs>
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传项目选择弹窗 */}
      <Modal
        title="上传脚本"
        open={uploadProjectModalVisible}
        onOk={confirmUpload}
        onCancel={() => {
          setUploadProjectModalVisible(false);
          setPendingUploadFile(null);
          uploadProjectForm.resetFields();
        }}
        okText="确认上传"
        cancelText="取消"
        width={400}
      >
        <Form form={uploadProjectForm} layout="vertical">
          <Form.Item
            name="name"
            label="脚本名称"
            rules={[{ required: true, message: '请输入脚本名称' }]}
          >
            <Input placeholder="脚本名称" />
          </Form.Item>
          <Form.Item
            name="project"
            label="所属项目"
            rules={[{ required: true, message: '请选择项目' }]}
          >
            <Select placeholder="请选择项目">
              {projectList.map(p => (
                <Option key={p.id} value={p.id}>{p.name}</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

export default TestScriptList;
