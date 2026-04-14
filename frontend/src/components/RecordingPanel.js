import React, { useState, useCallback, useEffect } from 'react';
import {
  Modal,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Spin,
  Card,
  Row,
  Col,
  Input,
  Select,
  Form,
  List,
  Empty,
  Popconfirm,
} from 'antd';
import {
  PlayCircleOutlined,
  SaveOutlined,
  DeleteOutlined,
  EditOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { uiTestsAPI } from '../api/uiTests';
import { useProjects } from '../hooks/useProjects';
import ProjectSelect from './FormFields/ProjectSelect';

const { Text, Title } = Typography;

/**
 * 录制面板组件 - 同步阻塞模式
 * 
 * 流程：
 * 1. 用户输入URL并开始录制 (config阶段)
 * 2. 前端发起同步请求，显示加载中 (recording阶段)
 * 3. 浏览器窗口关闭后，请求返回步骤，用户预览/编辑 (recording阶段的展示部分)
 * 4. 保存脚本 (saving阶段)
 */
const RecordingPanel = ({ visible, onClose, onSave }) => {
  const { projects, loading: projectsLoading } = useProjects();
  
  // 阶段状态：'config' | 'recording' | 'saving'
  const [stage, setStage] = useState('config');
  const [isLoading, setIsLoading] = useState(false);
  const [localSteps, setLocalSteps] = useState([]);
  const [qualityResult, setQualityResult] = useState(null);

  // 编辑步骤相关
  const [editingStepIndex, setEditingStepIndex] = useState(null);
  const [editStepForm] = Form.useForm();

  // 配置表单
  const [configForm] = Form.useForm();
  const [saveForm] = Form.useForm();

  // 重置状态
  const resetState = useCallback(() => {
    setStage('config');
    setIsLoading(false);
    setLocalSteps([]);
    setQualityResult(null);
    setEditingStepIndex(null);
    configForm.resetFields();
    saveForm.resetFields();
    editStepForm.resetFields();
  }, [configForm, saveForm, editStepForm]);

  // 当Modal关闭时重置状态
  useEffect(() => {
    if (!visible) {
      resetState();
    }
  }, [visible, resetState]);

  // 开始同步录制
  const handleStartSyncRecord = async (values) => {
    try {
      setIsLoading(true);
      setStage('recording');
      message.loading({ content: '正在启动浏览器进行录制，请在弹出窗口中完成操作并关闭窗口...', key: 'sync_record', duration: 0 });

      const res = await uiTestsAPI.syncRecord({
        start_url: values.startUrl,
        browser_type: values.browserType || 'chromium',
      });

      if (res.data.success) {
        const steps = res.data.steps || [];
        setLocalSteps(steps);

        // 录制完成后，立即进行一次“脚本质量检查”（非实时，只在录制结束后调用）
        try {
          const qualityRes = await uiTestsAPI.qualityCheck({
            actions: steps,
            browser_type: values.browserType || 'chromium',
          });
          setQualityResult(qualityRes.data.quality || null);
        } catch (e) {
          // 质量检查失败时，不阻塞后续流程，但给出提示
          message.warning(e.response?.data?.error || '脚本质量检查失败，可稍后重试');
        }

        message.success({ content: res.data.message || '录制完成', key: 'sync_record', duration: 3 });
      } else {
        message.error({ content: '录制异常：' + (res.data.error || '未知错误'), key: 'sync_record', duration: 5 });
        setStage('config');
      }
    } catch (err) {
      message.error({ content: err.response?.data?.error || '录制请求失败，请检查服务状态', key: 'sync_record', duration: 5 });
      setStage('config');
    } finally {
      setIsLoading(false);
    }
  };

  // 进入保存阶段
  const handleProceedToSave = () => {
    if (localSteps.length === 0) {
      message.warning('没有录制到任何步骤');
      return;
    }

    // 如果存在质量检查结果且包含错误，给出友好提示，让用户确认是否继续保存
    if (qualityResult && qualityResult.summary?.error_count > 0) {
      const errorCount = qualityResult.summary.error_count;
      Modal.confirm({
        title: '脚本质量检查未通过',
        content: `当前脚本存在 ${errorCount} 个错误级问题，建议根据提示先修改步骤再保存。仍然要继续保存吗？`,
        okText: '仍然保存',
        cancelText: '返回调整',
        onOk: () => setStage('saving'),
      });
      return;
    }

    setStage('saving');
  };

  // 删除步骤
  const handleDeleteStep = (index) => {
    const newSteps = localSteps.filter((_, i) => i !== index);
    const reorderedSteps = newSteps.map((step, idx) => ({
      ...step,
      order: idx + 1,
      id: step.id || `action_${idx + 1}`,
    }));
    setLocalSteps(reorderedSteps);
    message.success('步骤已删除');
  };

  // 开始编辑步骤
  const handleEditStep = (index) => {
    const step = localSteps[index];
    setEditingStepIndex(index);

    editStepForm.setFieldsValue({
      description: step.description || '',
      locator_type: typeof step.selector === 'string' ? 'css' : (step.selector?.type || 'css'),
      locator_value: typeof step.selector === 'string' ? step.selector : (step.selector?.value || ''),
      param_value: step.params?.value || '',
      param_url: step.params?.url || '',
    });
  };

  // 保存编辑的步骤
  const handleSaveEditedStep = () => {
    editStepForm.validateFields().then((values) => {
      const newSteps = [...localSteps];
      const step = { ...newSteps[editingStepIndex] };

      step.description = values.description || '';

      // 保持选择器对象结构 (类型+值)
      step.selector = {
        type: values.locator_type || 'css',
        value: values.locator_value
      };

      // 确保 params 是对象，避免校验失败
      step.params = step.params || {};

      if (step.type === 'fill') {
        step.params = { ...step.params, value: values.param_value };
      } else if (step.type === 'navigate') {
        step.params = { ...step.params, url: values.param_url };
      }

      newSteps[editingStepIndex] = step;
      setLocalSteps(newSteps);
      setEditingStepIndex(null);
      editStepForm.resetFields();
      message.success('步骤已更新');
    });
  };

  const handleCancelEdit = () => {
    setEditingStepIndex(null);
    editStepForm.resetFields();
  };

  // 保存脚本
  const handleSaveScript = async (values) => {
    try {
      setIsLoading(true);
      const actions = localSteps.map((step, index) => ({
        ...step,
        id: step.id || `action_${index + 1}`,
        order: step.order || index + 1,
      }));

      await uiTestsAPI.createScript({
        name: values.scriptName,
        description: values.description || '',
        project: values.project || null,
        browser_type: configForm.getFieldValue('browserType') || 'chromium',
        actions: actions,
      });

      message.success('脚本保存成功');
      if (onSave) onSave();
      if (onClose) onClose();
    } catch (err) {
      message.error(err.response?.data?.error || '保存脚本失败');
    } finally {
      setIsLoading(false);
    }
  };

  // --- 辅助函数：获取某个步骤的质量问题 ---
  const getStepIssues = useCallback((stepOrder) => {
    if (!qualityResult || !qualityResult.issues) return [];
    return qualityResult.issues.filter((issue) => issue.order === stepOrder);
  }, [qualityResult]);

  // --- 渲染部分 ---

  const renderConfigStage = () => (
    <Card title="录制配置" bordered={false} style={{ maxWidth: 600, margin: '0 auto' }}>
      <Form
        form={configForm}
        layout="vertical"
        onFinish={handleStartSyncRecord}
        initialValues={{
          startUrl: 'https://www.baidu.com',
          browserType: 'chromium',
        }}
      >
        <Form.Item
          label="起始 URL"
          name="startUrl"
          rules={[{ required: true, message: '请输入起始URL' }]}
        >
          <Input placeholder="例如: https://www.baidu.com" size="large" />
        </Form.Item>

        <Form.Item
          label="浏览器类型"
          name="browserType"
          rules={[{ required: true, message: '请选择浏览器' }]}
        >
          <Select size="large">
            <Select.Option value="chromium">Chromium (推荐)</Select.Option>
            <Select.Option value="firefox">Firefox</Select.Option>
            <Select.Option value="webkit">WebKit (Safari内核)</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item style={{ marginTop: 24 }}>
          <Button type="primary" htmlType="submit" loading={isLoading} size="large" block icon={<PlayCircleOutlined />}>
            开始同步录制
          </Button>
          <Text type="secondary" style={{ display: 'block', marginTop: 12, textAlign: 'center' }}>
            启动后请在弹出的浏览器中操作，关闭浏览器窗口即完成录制。
          </Text>
        </Form.Item>
      </Form>
    </Card>
  );

  const renderRecordingStage = () => (
    <Spin spinning={isLoading} tip="录制中，请在弹出窗口操作并关闭浏览器...">
      <div style={{ minHeight: 400 }}>
        {localSteps.length > 0 ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Row justify="space-between" align="middle">
              <Col>
                <Title level={4}>已录制步骤 ({localSteps.length})</Title>
              </Col>
              <Col>
                <Space>
                  <Button onClick={() => setStage('config')}>重新录制</Button>
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleProceedToSave}>
                    进入保存
                  </Button>
                </Space>
              </Col>
            </Row>

            {/* 质量检查结果摘要 */}
            {qualityResult && (
              <Card 
                size="small" 
                type="inner"
                style={{
                  borderColor: qualityResult.summary?.error_count > 0 
                    ? '#ff4d4f' 
                    : qualityResult.summary?.warning_count > 0 
                      ? '#faad14' 
                      : '#52c41a',
                  borderWidth: 2,
                }}
              >
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Space size="small" wrap>
                    <Text strong>脚本质量检查结果：</Text>
                    {qualityResult.summary?.error_count > 0 ? (
                      <Tag icon={<CloseCircleOutlined />} color="error">
                        有 {qualityResult.summary.error_count} 个错误，必须修复后才能正常执行
                      </Tag>
                    ) : qualityResult.summary?.warning_count > 0 ? (
                      <Tag icon={<WarningOutlined />} color="warning">
                        有 {qualityResult.summary.warning_count} 个警告，建议检查
                      </Tag>
                    ) : (
                      <Tag color="success">全部通过</Tag>
                    )}
                  </Space>
                  
                  {qualityResult.summary?.error_count > 0 && (
                    <div style={{ padding: '8px 12px', backgroundColor: '#fff2f0', borderRadius: 4 }}>
                      <Text type="danger" strong>
                        请查看下方步骤列表中标红的步骤，修复后再保存脚本。
                      </Text>
                    </div>
                  )}
                </Space>
              </Card>
            )}

            <List
              grid={{ gutter: 16, column: 1 }}
              dataSource={localSteps}
              renderItem={(step, index) => {
                const stepOrder = step.order || index + 1;
                const stepIssues = getStepIssues(stepOrder);
                const hasError = stepIssues.some((i) => i.level === 'error');
                const hasWarning = stepIssues.some((i) => i.level === 'warning');
                
                // 根据问题级别设置边框颜色
                let borderStyle = {};
                if (hasError) {
                  borderStyle = { border: '2px solid #ff4d4f', backgroundColor: '#fff2f0' };
                } else if (hasWarning) {
                  borderStyle = { border: '2px solid #faad14', backgroundColor: '#fffbe6' };
                }

                return (
                  <List.Item>
                    <Card 
                      size="small"
                      style={borderStyle}
                      actions={[
                        <Button type="link" icon={<EditOutlined />} onClick={() => handleEditStep(index)}>编辑</Button>,
                        <Popconfirm title="确定删除？" onConfirm={() => handleDeleteStep(index)}>
                          <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                        </Popconfirm>
                      ]}
                    >
                      <Space size="small" style={{ marginBottom: 8 }}>
                        <Tag color="blue">{stepOrder}</Tag>
                        <Text strong>{step.type.toUpperCase()}</Text>
                        <Text type="secondary">{step.description}</Text>
                        {hasError && <Tag icon={<CloseCircleOutlined />} color="error">有错误</Tag>}
                        {!hasError && hasWarning && <Tag icon={<WarningOutlined />} color="warning">有警告</Tag>}
                      </Space>
                      
                      <div style={{ fontSize: '12px', color: '#888' }}>
                        {step.selector && (
                          <div>
                            选择器: <code>{typeof step.selector === 'string' ? step.selector : JSON.stringify(step.selector)}</code>
                          </div>
                        )}
                        {step.params && Object.keys(step.params).length > 0 && (
                          <div>参数: <code>{JSON.stringify(step.params)}</code></div>
                        )}
                      </div>

                      {/* 直接在步骤卡片内显示该步骤的质量问题 */}
                      {stepIssues.length > 0 && (
                        <div style={{ marginTop: 8, padding: '8px', backgroundColor: hasError ? '#fff1f0' : '#fffbe6', borderRadius: 4 }}>
                          {stepIssues.map((issue, idx) => (
                            <div key={idx} style={{ marginBottom: idx < stepIssues.length - 1 ? 6 : 0 }}>
                              <Space size={4}>
                                {issue.level === 'error' ? (
                                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                                ) : (
                                  <WarningOutlined style={{ color: '#faad14' }} />
                                )}
                                <Text type={issue.level === 'error' ? 'danger' : 'warning'} style={{ fontSize: 12 }}>
                                  {issue.message}
                                </Text>
                              </Space>
                              {issue.suggestion && (
                                <div style={{ marginLeft: 18, fontSize: 11, color: '#666' }}>
                                  建议：{issue.suggestion}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  </List.Item>
                );
              }}
            />
          </Space>
        ) : !isLoading && (
          <Empty description="未录制到任何有效步骤，请重试。" style={{ marginTop: 100 }}>
            <Button type="primary" onClick={() => setStage('config')}>返回配置</Button>
          </Empty>
        )}
      </div>

      <Modal
        title={`编辑步骤 ${editingStepIndex + 1}`}
        open={editingStepIndex !== null}
        onOk={handleSaveEditedStep}
        onCancel={handleCancelEdit}
        okText="保存更改"
        cancelText="取消"
      >
        {editingStepIndex !== null && (
          <Form form={editStepForm} layout="vertical">
            <Form.Item label="操作描述" name="description">
              <Input />
            </Form.Item>
            <Form.Item label="选择器" name="locator_value">
              <Input />
            </Form.Item>
            {localSteps[editingStepIndex]?.type === 'fill' && (
              <Form.Item label="输入值" name="param_value">
                <Input />
              </Form.Item>
            )}
            {localSteps[editingStepIndex]?.type === 'navigate' && (
              <Form.Item label="跳转URL" name="param_url">
                <Input />
              </Form.Item>
            )}
          </Form>
        )}
      </Modal>
    </Spin>
  );

  const renderSavingStage = () => (
    <Card title="保存为测试脚本" bordered={false} style={{ maxWidth: 600, margin: '0 auto' }}>
      <Form
        form={saveForm}
        layout="vertical"
        onFinish={handleSaveScript}
        initialValues={{
          scriptName: `录制脚本_${new Date().toLocaleTimeString()}`,
        }}
      >
        <Form.Item label="脚本名称" name="scriptName" rules={[{ required: true }]}>
          <Input size="large" />
        </Form.Item>
        <Form.Item label="详细描述" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
        <ProjectSelect 
          projects={projects} 
          required={true}
          loading={projectsLoading}
        />
        <div style={{ textAlign: 'right', marginTop: 24 }}>
          <Space>
            <Button onClick={() => setStage('recording')}>返回调整步骤</Button>
            <Button type="primary" htmlType="submit" loading={isLoading} size="large">
              确认并保存
            </Button>
          </Space>
        </div>
      </Form>
    </Card>
  );

  return (
    <Modal
      title="同步录制模式 (最简逻辑)"
      open={visible}
      onCancel={onClose}
      destroyOnClose
      width={stage === 'recording' ? 800 : 700}
      footer={null}
      style={{ top: 50 }}
    >
      {stage === 'config' && renderConfigStage()}
      {stage === 'recording' && renderRecordingStage()}
      {stage === 'saving' && renderSavingStage()}
    </Modal>
  );
};

export default RecordingPanel;
