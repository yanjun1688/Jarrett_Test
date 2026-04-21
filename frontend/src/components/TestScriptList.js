import React, { useReducer, useEffect, useCallback, useState } from 'react';
import apiClient from '../api/axios';
import { Table, Button, Upload, Card, Space, Typography, Tag, notification, Descriptions, Modal, Input, Form, Select, Collapse, Tabs, Divider } from 'antd';
import { UploadOutlined, EditOutlined, QuestionCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import { usePermissions } from '../hooks/usePermissions';
import { unifiedExecutionsAPI } from '../api/unifiedExecutions';
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
    steps: [],
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
    steps: [],
    teardown: []
  });
  const { hasCrudPermission } = usePermissions();
  const [uploadProjectModalVisible, setUploadProjectModalVisible] = useState(false);
  const [uploadProjectForm] = Form.useForm();
  const [pendingUploadFile, setPendingUploadFile] = useState(null);
  const [pendingScriptType, setPendingScriptType] = useState('yaml');
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [logModalData, setLogModalData] = useState({ logs: [], loading: false, scriptName: '' });

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

      // 根据脚本内部测试用例的实际执行结果展示通知
      if (response.data.success) {
        notification.success({ message: '脚本执行完成', description: '所有测试用例通过' });
      } else {
        // 统计失败步骤信息
        const results = response.data.results || [];
        const failedCount = results.filter(r => !r.success).length;
        const totalCount = results.length;
        const description = totalCount > 0
          ? `${totalCount} 个步骤中有 ${failedCount} 个失败`
          : response.data.error || '测试用例执行失败，请查看日志';
        notification.warning({
          message: '脚本执行完成，存在失败用例',
          description,
          duration: 6,
        });
      }

      fetchScripts(); // Refresh list to update status
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message;
      dispatch({ type: 'EXECUTE_ERROR', payload: { success: false, output: '', error_message: errorMsg } });
      notification.error({ message: '脚本执行异常', description: errorMsg });
    }
  };

  const handleViewLogs = async (scriptId, scriptName) => {
    setLogModalData({ logs: [], loading: true, scriptName });
    setLogModalVisible(true);
    try {
      const response = await unifiedExecutionsAPI.getAll({ script_type: 'script' });
      const allExecutions = response.data?.results || response.data || [];
      // 过滤出当前脚本的执行记录（通过 script_name 匹配）
      const scriptExecutions = allExecutions.filter(e => e.script_name === scriptName);
      setLogModalData({ logs: scriptExecutions, loading: false, scriptName });
    } catch (error) {
      notification.error({ message: '获取执行日志失败', description: error.message });
      setLogModalData({ logs: [], loading: false, scriptName });
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
        steps: parsed.steps || parsed.test_steps || [],
        teardown: parsed.teardown || [],
      });
      setEditComposeContent(content);
    } catch (e) {
      setEditComposeContent(script.content || '');
      setEditVisualFormData({
        variables: {},
        setup: [],
        steps: [],
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
        if (editVisualFormData.steps?.length) scriptObj.steps = editVisualFormData.steps;
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

        if (visualFormData.steps && visualFormData.steps.length > 0) {
          scriptObj.steps = visualFormData.steps;
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
        steps: [],
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

    if (visualFormData.steps && visualFormData.steps.length > 0) {
      scriptObj.steps = visualFormData.steps;
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
          <Button icon={<FileTextOutlined />} onClick={() => handleViewLogs(record.id, record.name)}>
            日志
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
                <strong>测试脚本使用说明</strong>
              </Space>
            } 
            key="usage-guide"
          >
            <div style={{ padding: '16px 0' }}>
              <Typography.Paragraph>
                <Title level={4}>功能概述</Title>
                <p>
                  测试脚本支持通过 <strong>YAML</strong> 或 <strong>JSON</strong> 格式编写 API 测试链路。
                  支持变量管理、Setup/Teardown 阶段、变量提取和断言验证。
                </p>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>脚本结构（YAML 格式）</Title>
                <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto', fontSize: 13 }}>
{`name: 用户登录测试
description: 测试描述
variables:
  base_url: "https://api.example.com"

setup:
  - name: 前置登录
    request:
      method: POST
      url: "{{base_url}}/login"
      json:
        username: test
        password: "123"
    extract:
      - name: token
        jsonpath: "$.data.token"
    assertions:
      - type: status_code
        expected: 200
        comparison: equals

steps:
  - name: 获取用户信息
    request:
      method: GET
      url: "{{base_url}}/user"
      headers:
        Authorization: "Bearer {{token}}"
    assertions:
      - type: jsonpath
        expression: "$.code"
        expected: 0
        comparison: equals

teardown:
  - name: 清理数据
    request:
      method: POST
      url: "{{base_url}}/logout"`}
                </pre>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>核心功能</Title>
                <ul>
                  <li><strong>变量管理</strong>：在 <code>variables</code> 中定义初始变量，使用 <code>{"{{var}}"}</code> 模板语法引用</li>
                  <li><strong>变量提取</strong>：通过 <code>extract</code> + JSONPath 从响应中提取值供后续步骤使用</li>
                  <li><strong>Setup/Teardown</strong>：前置准备和后置清理阶段，Setup 失败则跳过测试步骤，Teardown 始终执行</li>
                  <li><strong>断言验证</strong>：<code>status_code</code> 状态码断言、<code>jsonpath</code> JSON 路径断言，必须指定 <code>comparison</code> 比较方式</li>
                </ul>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>断言配置</Title>
                <p>断言必须包含三个字段：<code>type</code>、<code>expected</code>、<code>comparison</code></p>
                <ul>
                  <li><strong>type</strong>：<code>status_code</code> 或 <code>jsonpath</code></li>
                  <li><strong>expected</strong>：期望值</li>
                  <li><strong>comparison</strong>：<code>equals</code>、<code>not_equals</code>、<code>contains</code>、<code>gt</code>、<code>gte</code>、<code>lt</code>、<code>lte</code></li>
                  <li>JSONPath 断言还需 <code>expression</code> 字段指定路径</li>
                </ul>
              </Typography.Paragraph>

              <Typography.Paragraph>
                <Title level={4}>操作方式</Title>
                <ul>
                  <li><strong>可视化编辑器</strong>：通过表单配置变量、步骤，点击"生成代码预览"查看 JSON</li>
                  <li><strong>代码编辑器</strong>：直接编写 JSON 格式脚本内容</li>
                  <li><strong>上传脚本</strong>：上传已有的 .json 或 .yaml 文件</li>
                  <li><strong>查看日志</strong>：点击"日志"按钮查看脚本执行历史记录</li>
                </ul>
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
                      steps={editVisualFormData.steps || []}
                      onChange={(steps) => updateEditVisualFormField('steps', steps)}
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
                      steps={visualFormData.steps || []}
                      onChange={(steps) => updateVisualFormField('steps', steps)}
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
                                    expected: 200,
                                    comparison: "equals"
                                  }
                                ]
                              }
                            ],
                            steps: [
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
                                    expected: 200,
                                    comparison: "equals"
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
                  placeholder={'在此处输入YAML或JSON格式的测试脚本，例如:\n\nname: 用户下单流程测试\ndescription: 完整用户注册-登录-下单流程\n\nvariables:\n  username: test_user_001\n  password: 123456\n\nsteps:\n  - name: 用户注册\n    request:\n      method: POST\n      url: https://api.example.com/register\n      json:\n        username: {{username}}\n        password: {{password}}\n    extract:\n      - name: user_id\n        jsonpath: $.data.user_id\n    assertions:\n      - type: status_code\n        expected: 200\n        comparison: equals'}
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

      {/* 执行日志弹窗 */}
      <Modal
        title={`执行日志 - ${logModalData.scriptName}`}
        open={logModalVisible}
        onCancel={() => setLogModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setLogModalVisible(false)}>关闭</Button>
        ]}
        width={900}
      >
        {logModalData.loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : logModalData.logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无执行记录</div>
        ) : (
          logModalData.logs.map((exec) => (
            <Card
              key={exec.id}
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Space>
                  <Tag color={exec.status === 'passed' ? 'green' : exec.status === 'failed' ? 'red' : 'default'}>
                    {exec.status_display || exec.status}
                  </Tag>
                  <span>{exec.started_at ? new Date(exec.started_at).toLocaleString() : '未知时间'}</span>
                  {exec.duration_seconds && <span style={{ color: '#999' }}>耗时: {exec.duration_seconds.toFixed(2)}s</span>}
                </Space>
              }
            >
              {exec.error_message && (
                <div style={{ color: '#ff4d4f', marginBottom: 8 }}>错误: {exec.error_message}</div>
              )}
              {exec.logs ? (
                <Card style={{ background: '#f5f5f5', maxHeight: 300, overflow: 'auto' }}>
                  <pre style={{ fontFamily: 'monospace', fontSize: 12, margin: 0, whiteSpace: 'pre-wrap' }}>
                    {exec.logs}
                  </pre>
                </Card>
              ) : (
                <div style={{ color: '#999' }}>无日志</div>
              )}
            </Card>
          ))
        )}
      </Modal>
    </Space>
  );
}

export default TestScriptList;
