import React, { useState } from 'react';
import { Card, Input, Button, message, Space, Select, Form, Steps, Tag, Modal, Descriptions } from 'antd';
import { PlayCircleOutlined, SaveOutlined, PlaySquareOutlined, FileTextOutlined } from '@ant-design/icons';
import { agentAPI, testFlowAPI } from '../api';
import PageStructureEditor from './PageStructureEditor';
import { pageStructureAPI } from '../api/pageStructure';
import { useProjects } from '../hooks/useProjects';

const { TextArea } = Input;

const NODE_TYPE_COLORS = {
  ui_test: 'blue',
  api_test: 'green',
  data_generation: 'purple',
  validation: 'orange',
  report: 'cyan'
};

const NODE_TYPE_LABELS = {
  ui_test: 'UI测试',
  api_test: 'API测试',
  data_generation: '数据生成',
  validation: '验证',
  report: '报告'
};

const TestFlowBuilder = () => {
  const { projects, loading: projectsLoading } = useProjects();
  
  const [flow, setFlow] = useState({ nodes: [], start_node: null, metadata: {} });
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [scenario, setScenario] = useState('');
  const [testType, setTestType] = useState('ui_test');
  const [projectId, setProjectId] = useState('');
  const [flowId, setFlowId] = useState(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingNode] = useState(null);
  const [form] = Form.useForm();

  // 页面结构管理相关状态
  const [url, setUrl] = useState('');
  const [pageStructureVisible, setPageStructureVisible] = useState(false);
  const [hasPageStructure, setHasPageStructure] = useState(false);
  const [checkingPageStructure, setCheckingPageStructure] = useState(false);

  const handleNodeUpdate = async () => {
    try {
      const values = form.getFieldsValue();
      console.log('[FRONTEND] Updating node:', editingNode?.id, values);
      setEditModalVisible(false);
      message.success('节点更新成功');
    } catch (error) {
      console.error('[FRONTEND] Node update error:', error);
      message.error('节点更新失败');
    }
  };

  // 检查页面结构是否存在
  const checkPageStructure = async (urlToCheck, projectIdToCheck) => {
    if (!urlToCheck || !projectIdToCheck || testType !== 'ui_test') {
      setHasPageStructure(false);
      return;
    }

    // 统一URL格式：去掉末尾斜杠
    const normalizedUrl = urlToCheck.replace(/\/$/, '');
    
    setCheckingPageStructure(true);
    try {
      const exists = await pageStructureAPI.checkPageStructureExists(normalizedUrl, parseInt(projectIdToCheck));
      setHasPageStructure(exists);
      if (exists) {
        message.success('已找到页面结构，AI将基于页面元素生成准确的选择器');
      }
    } catch (error) {
      console.error('检查页面结构失败:', error);
    } finally {
      setCheckingPageStructure(false);
    }
  };

  // URL变化时检查页面结构
  const handleUrlChange = (e) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    if (newUrl && projectId) {
      checkPageStructure(newUrl, projectId);
    }
  };

  // 项目变化时检查页面结构
  const handleProjectChange = (value) => {
    setProjectId(value);
    if (url && value) {
      checkPageStructure(url, value);
    }
  };

  const handleGenerateFlow = async () => {
    if (!scenario.trim()) {
      message.error('请输入场景描述');
      return;
    }

    // UI测试需要URL
    if (testType === 'ui_test' && !url.trim()) {
      message.error('UI测试需要输入目标URL');
      return;
    }

    setIsGenerating(true);
    try {
      const params = {
        description: scenario.trim(),
        project_id: projectId,
        test_type: testType
      };

      // UI测试时添加URL和启用RAG（去掉末尾斜杠统一格式）
      if (testType === 'ui_test' && url) {
        params.additional_context = { url: url.trim().replace(/\/$/, '') };
        params.use_rag = true;
      }

      console.log('[FRONTEND] Calling planTestFlow with:', params);
      const response = await agentAPI.planTestFlow(params);

      console.log('[FRONTEND] Plan flow response:', response);

      if (response.success) {
        setFlow(response.flow_ir); // 新接口返回 flow_ir
        // 注意：新接口可能不会直接返回 flow_id，因为推荐直接执行 FlowIR 而不保存
        setFlowId(null);
        message.success('流程规划成功');
        console.log('[FRONTEND] Flow planned successfully');
      } else {
        message.error(response.message || '流程规划失败');
      }
    } catch (error) {
      console.error('流程规划失败:', error);
      message.error('流程规划失败，请检查网络连接');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecuteFlow = async () => {
    console.log('[FRONTEND] ===== EXECUTE FLOW CLICKED =====');
    console.log('[FRONTEND] flow:', flow);

    if (!flow) {
      console.error('[FRONTEND] No flow, cannot execute');
      message.error('请先生成流程');
      return;
    }

    console.log('[FRONTEND] Starting flow execution...');
    setIsExecuting(true);
    try {
      console.log('[FRONTEND] Calling API: executeFlowIR with flowIR:', flow);
      const response = await agentAPI.executeFlowIR({
        flow_ir: flow
      });

      console.log('[FRONTEND] API response:', response);

      if (response.success) {
        message.success('流程执行成功');
        if (response.execution_id) {
          console.log('[FRONTEND] Redirecting to monitor page:', response.execution_id);
          window.location.href = `/test-flows/monitor/${response.execution_id}`;
        } else {
          message.success('流程执行完成');
        }
      } else {
        console.error('[FRONTEND] API returned error:', response.message);
        message.error(response.message || '流程执行失败');
      }
    } catch (error) {
      console.error('[FRONTEND] Execute flow error:', error);
      console.error('[FRONTEND] Error details:', {
        message: error.message,
        stack: error.stack,
        response: error.response?.data
      });
      message.error('流程执行失败，请检查网络连接');
    } finally {
      console.log('[FRONTEND] Execution completed, resetting state');
      setIsExecuting(false);
    }
  };

  const handleSaveFlow = async () => {
    if (!flowId || flow.nodes.length === 0) {
      message.error('请先生成流程');
      return;
    }

    setIsSaving(true);
    try {
      await testFlowAPI.saveTestFlow({
        flow_id: flowId,
        flow_data: flow
      });
      message.success('流程保存成功');
    } catch (error) {
      console.error('流程保存失败:', error);
      message.error('流程保存失败');
    } finally {
      setIsSaving(false);
    }
  };


  return (
    <div className="test-flow-builder" style={{ padding: 24 }}>
      <Card title="AI智能测试流程生成" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Form.Item
            name="testType"
            label="测试类型"
            required
          >
            <Select
              placeholder="请选择测试类型"
              style={{ width: 200 }}
              value={testType}
              onChange={(value) => setTestType(value)}
            >
              <Select.Option value="ui_test">UI测试</Select.Option>
              <Select.Option value="api_test">API测试</Select.Option>
            </Select>
          </Form.Item>
          {/* UI测试时显示URL输入和页面结构管理 */}
          {testType === 'ui_test' && (
            <>
              <Form.Item
                name="url"
                label="目标URL"
                rules={[{ required: true, message: '请输入目标URL' }]}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Input
                    placeholder="https://www.example.com"
                    value={url}
                    onChange={handleUrlChange}
                  />
                  <Space>
                    <Button
                      type="dashed"
                      icon={<FileTextOutlined />}
                      onClick={() => setPageStructureVisible(true)}
                      disabled={!url}
                      loading={checkingPageStructure}
                    >
                      {hasPageStructure ? '更新页面结构' : '管理页面结构'}
                    </Button>
                    {hasPageStructure && (
                      <Tag color="success">已保存</Tag>
                    )}
                    {!hasPageStructure && url && (
                      <Tag color="warning">未保存页面结构</Tag>
                    )}
                  </Space>
                  <div style={{ fontSize: 12, color: '#999' }}>
                    {!hasPageStructure 
                      ? '提示：首次测试前请先保存页面结构，AI将基于真实页面元素生成准确的选择器' 
                      : '页面结构已保存，AI将基于页面元素生成准确的选择器'}
                  </div>
                </Space>
              </Form.Item>
            </>
          )}

          <Form.Item
            name="scenario"
            label="场景描述"
            rules={[{ required: true, message: '请输入场景描述' }]}
          >
            <TextArea
              rows={4}
              placeholder={testType === 'ui_test' 
                ? "请描述UI测试场景，例如：'打开百度，在搜索框输入成都天气，点击百度一下按钮'"
                : "请描述API测试场景，例如：'测试登录API，验证用户名密码正确时返回token'"
              }
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            />
          </Form.Item>
          <Form.Item name="projectId" label="项目选择" rules={[{ required: true, message: '请选择项目' }]}>
            <Select
              placeholder="请选择项目"
              style={{ width: 300 }}
              value={projectId}
              onChange={handleProjectChange}
              loading={projectsLoading}
            >
              {projects.map((p) => (
                <Select.Option key={p.id} value={String(p.id)}>{p.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleGenerateFlow}
                loading={isGenerating}
              >
                生成流程
              </Button>
              <Button
                icon={<SaveOutlined />}
                onClick={handleSaveFlow}
                loading={isSaving}
                disabled={!flow}
              >
                保存流程
              </Button>
              <Button
                type="primary"
                icon={<PlaySquareOutlined />}
                onClick={handleExecuteFlow}
                loading={isExecuting}
                disabled={!flow}
              >
                执行流程
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {flow.nodes && Object.keys(flow.nodes).length > 0 && (
        <Card title={`测试流程步骤 (${Object.keys(flow.nodes).length}个节点)`}>
          <Steps
            direction="vertical"
            current={-1}
            items={Object.values(flow.nodes).map((node, index) => ({
              title: (
                <div>
                  <Tag color={NODE_TYPE_COLORS[node.node_type]}>{NODE_TYPE_LABELS[node.node_type]}</Tag>
                  {node.metadata?.name || node.node_type}
                </div>
              ),
              description: (
                <div>
                  <div style={{ marginBottom: 8 }}>{node.description || '无描述'}</div>
                  <Card size="small" style={{ backgroundColor: '#fafafa' }}>
                    <Descriptions column={1} size="small">
                      {node.parameters && Object.keys(node.parameters).length > 0 && (
                        <Descriptions.Item label="参数">
                          <pre style={{ margin: 0, fontSize: 12, maxHeight: 150, overflow: 'auto' }}>
                            {JSON.stringify(node.parameters, null, 2)}
                          </pre>
                        </Descriptions.Item>
                      )}
                      {node.on_success && (
                        <Descriptions.Item label="成功后">跳转到节点 {node.on_success}</Descriptions.Item>
                      )}
                      {node.on_failure && (
                        <Descriptions.Item label="失败后">跳转到节点 {node.on_failure}</Descriptions.Item>
                      )}
                    </Descriptions>
                  </Card>
                </div>
              )
            }))}
          />
        </Card>
      )}

      <Modal
        title="编辑节点"
        open={editModalVisible}
        onOk={handleNodeUpdate}
        onCancel={() => setEditModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="metadata" label="节点信息">
            <Input placeholder="节点名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="节点描述" />
          </Form.Item>
          <Form.Item name="parameters" label="参数">
            <TextArea rows={6} placeholder="JSON格式的参数" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 页面结构管理弹窗 */}
      <PageStructureEditor
        visible={pageStructureVisible}
        onCancel={() => setPageStructureVisible(false)}
        onSuccess={(data) => {
          console.log('页面结构保存成功:', data);
          setHasPageStructure(true);
          setPageStructureVisible(false);
          message.success('页面结构已保存，可以开始生成测试流程了');
        }}
        projectId={projectId ? parseInt(projectId) : null}
        url={url}
        title={url ? (() => { try { return new URL(url).hostname; } catch { return url; } })() : ''}
      />
    </div>
  );
};

export default TestFlowBuilder;
