import React, { useCallback } from 'react';
import {
  Table,
  Button,
  Card,
  Space,
  Typography,
  Tag,
  notification,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Divider,
} from 'antd';
import { 
  PlayCircleOutlined, 
  EditOutlined, 
  VideoCameraAddOutlined,
} from '@ant-design/icons';
import { uiTestsAPI } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import RecordingPanel from './RecordingPanel';

import ExecutionModal from '../features/ui-tests/components/ExecutionModal';
import { buildStepsPayload, convertStepsToFormFormat } from '../features/ui-tests/utils/scriptUtils';
import useUiTestScripts from '../features/ui-tests/hooks/useUiTestScripts';
import useScriptModals from '../features/ui-tests/hooks/useScriptModals';
import { handleApiError } from '../utils/errorHandler';
import { ACTION_LABELS, BROWSER_TYPE_LABELS, DEFAULT_CONFIG } from '../constants';
import '../css/UiTestManager.css';

const { Title, Text } = Typography;
const { Option } = Select;

const UiTestManager = () => {
  // 使用提取的hooks
  const { loading, scripts, projects, loadScripts } = useUiTestScripts();
  const modalState = useScriptModals();
  const { dispatch: modalDispatch, ...modals } = modalState;

  const [form] = Form.useForm();
  const [executingId, setExecutingId] = React.useState(null);
  const { canEdit } = usePermissions();

  const {
    executionModalVisible,
    executionDetail,
    createModalVisible,
    editModalVisible,
    editingScript,
  } = modals;

  // 录制面板状态
  const [recordingPanelVisible, setRecordingPanelVisible] = React.useState(false);

  // 轮询执行状态的 ref（用于清理）
  const pollingRef = React.useRef(null);
  const pollingStartRef = React.useRef(null);
  const POLLING_TIMEOUT_MS = 2 * 60 * 1000; // 2分钟超时

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    pollingStartRef.current = null;
  }, []);

  // 轮询查询执行状态
  const pollExecutionStatus = useCallback(async (executionId) => {
    // 超时保护
    if (pollingStartRef.current && Date.now() - pollingStartRef.current > POLLING_TIMEOUT_MS) {
      stopPolling();
      setExecutingId(null);
      notification.warning({ message: '执行超时', description: '轮询已超过2分钟，请检查 Celery worker 是否正常运行' });
      return;
    }

    try {
      const res = await uiTestsAPI.getExecutionLogs(executionId);
      const detail = res.data;
      
      // 更新弹窗数据
      modalDispatch({ type: 'SHOW_EXECUTION', payload: detail });
      
      // 检查是否执行完成（非 running/pending 状态）
      if (detail.status && detail.status !== 'running' && detail.status !== 'pending') {
        stopPolling();
        setExecutingId(null);
        
        if (detail.status === 'passed') {
          notification.success({ message: 'UI 测试执行通过' });
        } else {
          notification.error({ message: 'UI 测试执行失败', description: detail.error_message || '' });
        }
        
        loadScripts();
      }
    } catch (err) {
      console.error('轮询执行状态失败:', err);
      // 轮询失败不停止，继续尝试
    }
  }, [modalDispatch, stopPolling, loadScripts]);

  // 执行脚本
  const handleExecute = useCallback(async (scriptId) => {
    setExecutingId(scriptId);
    stopPolling(); // 先停止之前的轮询
    
    try {
      const res = await uiTestsAPI.executeScript(scriptId);
      
      if (res.data.success && res.data.execution_id) {
        const executionId = res.data.execution_id;
        
        // 立即显示初始状态（pending/running）
        modalDispatch({ 
          type: 'SHOW_EXECUTION', 
          payload: {
            execution_id: executionId,
            script_name: res.data.script_name,
            status: res.data.status || 'pending',
            started_at: new Date().toISOString(),
          }
        });
        
        notification.info({ message: '任务已提交，正在执行中...', duration: 2 });
        
        // 开始轮询执行状态（每 2 秒查询一次）
        pollingStartRef.current = Date.now();
        pollingRef.current = setInterval(() => {
          pollExecutionStatus(executionId);
        }, 2000);
        
        // 立即查询一次
        setTimeout(() => pollExecutionStatus(executionId), 500);
        
      } else {
        // 执行失败，显示错误
        const errorMsg = res.data.error || '提交执行任务失败';
        notification.error({ message: '执行 UI 测试失败', description: errorMsg });
        setExecutingId(null);
      }
    } catch (err) {
      handleApiError(err, '执行 UI 测试失败');
      setExecutingId(null);
    }
  }, [modalDispatch, stopPolling, pollExecutionStatus]);

  // 组件卸载时停止轮询
  React.useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const closeCreateModal = () => {
    modalDispatch({ type: 'HIDE_CREATE' });
    form.resetFields();
  };

  // 编辑脚本
  const handleEdit = useCallback(async (script) => {
    try {
      // 获取脚本详情（包含步骤或代码）
      const res = await uiTestsAPI.getScriptById(script.id);
      const scriptDetail = res.data;
      
      // 转换步骤数据为表单格式
      const formSteps = convertStepsToFormFormat(scriptDetail.actions || []);
      
      form.setFieldsValue({
        name: scriptDetail.name,
        description: scriptDetail.description || '',
        project_id: scriptDetail.project,
        browser_type: scriptDetail.browser_type || DEFAULT_CONFIG.BROWSER_TYPE,
        headless: scriptDetail.headless !== false,
        steps: formSteps.length > 0 ? formSteps : [],
      });
      
      modalDispatch({ type: 'SHOW_EDIT', payload: scriptDetail });
    } catch (err) {
      handleApiError(err, '获取脚本详情失败');
    }
  }, [form, modalDispatch]);

  // 保存编辑
  const handleEditSubmit = async () => {
    try {
      const values = await form.validateFields();
      const scriptId = editingScript.id;
      
      // 更新基本信息和actions
      const stepsPayload = buildStepsPayload(values.steps || []);
      await uiTestsAPI.updateScript(scriptId, {
        name: values.name,
        description: values.description,
        project_id: values.project_id,
        browser_type: values.browser_type,
        headless: values.headless,
        actions: stepsPayload,
      });
      
      notification.success({ message: '脚本更新成功' });
      modalDispatch({ type: 'HIDE_EDIT' });
      form.resetFields();
      loadScripts();
    } catch (err) {
      handleApiError(err, '更新脚本失败');
    }
  };

  // 取消编辑
  const handleCancelEdit = () => {
    modalDispatch({ type: 'HIDE_EDIT' });
    form.resetFields();
  };

  // 录制面板回调函数
  const handleRecordingSave = useCallback(async () => {
    await loadScripts(); // 刷新脚本列表
    setRecordingPanelVisible(false);
  }, [loadScripts]);

  const handleCloseRecordingPanel = useCallback(() => {
    setRecordingPanelVisible(false);
  }, []);


  // 保存脚本（录制/可视化配置）
  const handleCreateSubmit = async () => {
    try {
      const values = await form.validateFields();

      const stepsPayload = buildStepsPayload(values.steps || []);

      const payload = {
        name: values.name,
        description: values.description || '',
        project: values.project || null,
        browser_type: values.browser_type,
        headless: values.headless,
        steps: stepsPayload,  // steps字段保存的是actions格式
        actions: stepsPayload,  // 直接传递actions格式（后端优先使用这个字段）
      };

      console.log('[UiTestManager] 保存脚本payload:', payload);
      const res = await uiTestsAPI.createScript(payload);

      notification.success({
        message: '创建 UI 测试脚本成功',
      });
      closeCreateModal();
      loadScripts();
      return res;
    } catch (err) {
      if (err?.errorFields) {
        // 表单校验错误
        return;
      }
      notification.error({
        message: '创建 UI 测试脚本失败',
        description: err.response?.data?.error || err.message,
      });
    }
  };

  // 表格列定义 - 使用useMemo优化
  const columns = React.useMemo(() => [
    {
      title: '脚本名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '所属项目',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (text) => text || '-',
    },
    {
      title: '浏览器',
      dataIndex: 'browser_type',
      key: 'browser_type',
      render: (value) => {
        if (!value) return '-';
        return BROWSER_TYPE_LABELS[value] || value;
      },
    },
    {
      title: '无头',
      dataIndex: 'headless',
      key: 'headless',
      render: (val) => (
        <Tag color={val ? 'blue' : 'green'}>{val ? '无头' : '可见'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (val) => (
        <Tag color={val ? 'green' : 'default'}>
          {val ? '启用' : '停用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) =>
        text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.id)}
            loading={executingId === record.id}
            disabled={!canEdit}
          >
            执行
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            disabled={!canEdit}
          >
            修改
          </Button>
        </Space>
      ),
    },
  ], [handleExecute, executingId, canEdit, handleEdit]);

  // 使用 useMemo 稳定 pagination 对象引用
  const paginationConfig = React.useMemo(() => ({ pageSize: 10 }), []);

  return (
    <Space direction="vertical" size="large" className="ui-test-container">
      <div className="ui-test-header">
        <Title level={2} className="ui-test-title">
          UI 测试管理
        </Title>
        <Button
          type="primary"
          icon={<VideoCameraAddOutlined />}
          onClick={() => setRecordingPanelVisible(true)}
          disabled={!canEdit}
        >
          录制脚本
        </Button>
      </div>

      <Card>
        <Title level={4}>说明</Title>
        <Text>
          这里的 UI 测试脚本是基于 Playwright 的
          “可视化步骤” 配置：不需要写代码，只要选择操作类型、元素和参数即可。
        </Text>
      </Card>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={scripts}
        loading={loading}
        pagination={paginationConfig}
      />

      {/* 执行结果弹窗 - 使用提取的组件 */}
      <ExecutionModal
        visible={executionModalVisible}
        executionDetail={executionDetail}
        onClose={() => {
          stopPolling(); // 关闭弹窗时停止轮询
          setExecutingId(null);
          modalDispatch({ type: 'HIDE_EXECUTION' });
        }}
      />

      {/* 新建脚本弹窗（可视化步骤配置） */}
      <Modal
        title="新建 UI 测试脚本"
        open={createModalVisible}
        onCancel={closeCreateModal}
        width={960}
        destroyOnClose
        footer={[
          <Button key="cancel" onClick={closeCreateModal}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            onClick={handleCreateSubmit}
            disabled={!canEdit}
          >
            保存脚本
          </Button>,
        ]}
      >
        <Form
          layout="vertical"
          form={form}
          initialValues={{ headless: DEFAULT_CONFIG.HEADLESS, browser_type: DEFAULT_CONFIG.BROWSER_TYPE }}
        >
          <Form.Item
            label="脚本名称"
            name="name"
            rules={[{ required: true, message: '请输入脚本名称' }]}
          >
            <Input placeholder="例如：登录并截图首页" />
          </Form.Item>

          <Form.Item label="脚本描述" name="description">
            <Input.TextArea
              rows={2}
              placeholder="给不会写代码的同事看一下这个脚本是做什么的"
            />
          </Form.Item>

          <Space size="large" className="ui-test-form-flex">
            <Form.Item
              label="所属项目"
              name="project"
              className="ui-test-form-flex-1"
              rules={[{ required: false }]}
            >
              <Select
                allowClear
                placeholder="可选：关联到某个项目"
              >
                {projects.map((p) => (
                  <Option key={p.id} value={p.id}>
                    {p.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="浏览器"
              name="browser_type"
              style={{ width: 200 }}
            >
              <Select>
                {Object.entries(BROWSER_TYPE_LABELS).map(([value, label]) => (
                  <Option key={value} value={value}>{label}</Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="无头模式"
              name="headless"
              valuePropName="checked"
            >
              <Switch checkedChildren="无头" unCheckedChildren="可见" />
            </Form.Item>
          </Space>

          <Divider />
          <Title level={4}>步骤配置（从上到下依次执行）</Title>

          <Form.List
            name="steps"
            rules={[
              {
                validator: async (_, steps) => {
                  if (!steps || steps.length === 0) {
                    return Promise.reject(
                      new Error('请至少添加一个步骤'),
                    );
                  }
                },
              },
            ]}
          >
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    className="ui-test-step-card"
                    title={`步骤 ${index + 1}`}
                    extra={
                      <Button
                        size="small"
                        danger
                        onClick={() => remove(field.name)}
                      >
                        删除
                      </Button>
                    }
                  >
                    <Space
                      direction="vertical"
                      className="ui-test-step-space"
                      size="small"
                    >
                      <Space className="ui-test-form-flex" align="baseline">
                        <Form.Item
                          {...field}
                          name={[field.name, 'action_type']}
                          fieldKey={[field.fieldKey, 'action_type']}
                          label="操作类型"
                          rules={[{ required: true, message: '请选择操作类型' }]}
                          className="ui-test-form-width-220"
                        >
                          <Select>
                            {Object.entries(ACTION_LABELS).map(
                              ([value, label]) => (
                                <Option key={value} value={value}>
                                  {label}
                                </Option>
                              ),
                            )}
                          </Select>
                        </Form.Item>

                        <Form.Item
                          {...field}
                          name={[field.name, 'description']}
                          fieldKey={[field.fieldKey, 'description']}
                          label="步骤说明"
                          className="ui-test-form-flex-1"
                        >
                          <Input placeholder="给这个步骤起个好理解的说明，方便别人看" />
                        </Form.Item>
                      </Space>

                      <Space className="ui-test-form-flex" align="baseline">
                        <Form.Item
                          {...field}
                          name={[field.name, 'locator_type']}
                          fieldKey={[field.fieldKey, 'locator_type']}
                          label="元素定位类型"
                          className="ui-test-form-width-200"
                        >
                          <Select allowClear placeholder="不需要元素可留空">
                            <Option value="id">ID</Option>
                            <Option value="name">Name</Option>
                            <Option value="css">CSS 选择器</Option>
                            <Option value="xpath">XPath</Option>
                            <Option value="text">文本</Option>
                            <Option value="testid">data-testid</Option>
                            <Option value="role">Role</Option>
                            <Option value="label">Label 文本</Option>
                          </Select>
                        </Form.Item>

                        <Form.Item
                          {...field}
                          name={[field.name, 'locator_value']}
                          fieldKey={[field.fieldKey, 'locator_value']}
                          label="元素值"
                          className="ui-test-form-flex-1"
                        >
                          <Input placeholder="例如：#login-button 或 .btn-primary" />
                        </Form.Item>

                      </Space>

                      {/* 针对不同操作类型显示不同参数字段（简单直观） */}
                      <Form.Item
                        noStyle
                        shouldUpdate={(prev, cur) =>
                          prev.steps?.[field.name]?.action_type !==
                          cur.steps?.[field.name]?.action_type
                        }
                      >
                        {({ getFieldValue }) => {
                          const currentAction =
                            getFieldValue(['steps', field.name, 'action_type']);

                          if (currentAction === 'navigate') {
                            return (
                              <Form.Item
                                {...field}
                                name={[field.name, 'url']}
                                fieldKey={[field.fieldKey, 'url']}
                                label="URL"
                                rules={[
                                  { required: true, message: '请输入要打开的地址' },
                                ]}
                              >
                                <Input placeholder="例如：https://example.com/login" />
                              </Form.Item>
                            );
                          }

                          if (
                            currentAction === 'fill' ||
                            currentAction === 'select'
                          ) {
                            return (
                              <Form.Item
                                {...field}
                                name={[field.name, 'value']}
                                fieldKey={[field.fieldKey, 'value']}
                                label="输入/选择的值"
                              >
                                <Input placeholder="例如：test_user 或 选项值" />
                              </Form.Item>
                            );
                          }

                          if (currentAction === 'wait') {
                            return (
                              <Space
                                style={{ display: 'flex' }}
                                align="baseline"
                              >
                                <Form.Item
                                  {...field}
                                  name={[field.name, 'wait_type']}
                                  fieldKey={[field.fieldKey, 'wait_type']}
                                  label="等待方式"
                                  initialValue="timeout"
                                  style={{ width: 200 }}
                                >
                                  <Select>
                                    <Option value="timeout">固定时间</Option>
                                    <Option value="selector">直到元素出现</Option>
                                    <Option value="navigation">页面加载完成</Option>
                                  </Select>
                                </Form.Item>

                                <Form.Item
                                  noStyle
                                  shouldUpdate={(prev, cur) =>
                                    prev.steps?.[field.name]?.wait_type !==
                                    cur.steps?.[field.name]?.wait_type
                                  }
                                >
                                  {({ getFieldValue: gf }) => {
                                    const wt = gf([
                                      'steps',
                                      field.name,
                                      'wait_type',
                                    ]);
                                    if (wt === 'timeout' || !wt) {
                                      return (
                                        <Form.Item
                                          {...field}
                                          name={[field.name, 'timeout']}
                                          fieldKey={[field.fieldKey, 'timeout']}
                                          label="等待毫秒数"
                                          initialValue={5000}
                                        >
                                          <Input
                                            type="number"
                                            min={0}
                                            placeholder="例如：5000 （5秒）"
                                          />
                                        </Form.Item>
                                      );
                                    }
                                    if (wt === 'selector') {
                                      return (
                                        <Form.Item
                                          {...field}
                                          name={[
                                            field.name,
                                            'wait_selector',
                                          ]}
                                          fieldKey={[
                                            field.fieldKey,
                                            'wait_selector',
                                          ]}
                                          label="等待的选择器"
                                        >
                                          <Input placeholder="例如：.loaded 或 #ready" />
                                        </Form.Item>
                                      );
                                    }
                                    return null;
                                  }}
                                </Form.Item>
                              </Space>
                            );
                          }

                          if (currentAction === 'screenshot') {
                            return (
                              <Form.Item
                                {...field}
                                name={[field.name, 'screenshotName']}
                                fieldKey={[
                                  field.fieldKey,
                                  'screenshotName',
                                ]}
                                label="截图名称（可选）"
                              >
                                <Input placeholder="例如：login-page" />
                              </Form.Item>
                            );
                          }

                          if (currentAction === 'assert') {
                            return (
                              <Space
                                style={{ display: 'flex' }}
                                align="baseline"
                              >
                                <Form.Item
                                  {...field}
                                  name={[field.name, 'assert_type']}
                                  fieldKey={[
                                    field.fieldKey,
                                    'assert_type',
                                  ]}
                                  label="断言类型"
                                  initialValue="text"
                                  style={{ width: 200 }}
                                >
                                  <Select>
                                    <Option value="text">文本包含</Option>
                                    <Option value="url">URL 包含</Option>
                                    <Option value="visible">
                                      元素可见/不可见
                                    </Option>
                                  </Select>
                                </Form.Item>
                                <Form.Item
                                  {...field}
                                  name={[field.name, 'expected_value']}
                                  fieldKey={[
                                    field.fieldKey,
                                    'expected_value',
                                  ]}
                                  label="期望值"
                                >
                                  <Input placeholder="例如：欢迎回来 / /dashboard" />
                                </Form.Item>
                              </Space>
                            );
                          }

                          if (currentAction === 'extract') {
                            return (
                              <Space
                                style={{ display: 'flex' }}
                                align="baseline"
                              >
                                <Form.Item
                                  {...field}
                                  name={[field.name, 'variable_name']}
                                  fieldKey={[
                                    field.fieldKey,
                                    'variable_name',
                                  ]}
                                  label="变量名"
                                >
                                  <Input placeholder="例如：loginToken" />
                                </Form.Item>
                                <Form.Item
                                  {...field}
                                  name={[field.name, 'attribute_name']}
                                  fieldKey={[
                                    field.fieldKey,
                                    'attribute_name',
                                  ]}
                                  label="属性名（可选）"
                                >
                                  <Input placeholder="仅在从属性提取时使用，例如 value" />
                                </Form.Item>
                              </Space>
                            );
                          }

                          return null;
                        }}
                      </Form.Item>
                    </Space>
                  </Card>
                ))}

                <Button
                  type="dashed"
                  block
                  onClick={() =>
                    add({
                      action_type: 'click',
                    })
                  }
                >
                  + 添加步骤
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      {/* 编辑模态框 */}
      <Modal
        title="编辑 UI 测试脚本"
        open={editModalVisible}
        onCancel={handleCancelEdit}
        width={960}
        destroyOnClose
        footer={[
          <Button key="cancel" onClick={handleCancelEdit}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            onClick={handleEditSubmit}
            disabled={!canEdit}
          >
            保存修改
          </Button>,
        ]}
      >
        {editingScript && (
          <Form
            form={form}
            layout="vertical"
            initialValues={{
            browser_type: DEFAULT_CONFIG.BROWSER_TYPE,
            headless: DEFAULT_CONFIG.HEADLESS,
            }}
          >
            <Form.Item
              name="name"
              label="脚本名称"
              rules={[{ required: true, message: '请输入脚本名称' }]}
            >
              <Input placeholder="例如：登录流程测试" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={2} placeholder="脚本描述（可选）" />
            </Form.Item>

            <Space size="large" style={{ display: 'flex' }}>
              <Form.Item
                label="所属项目"
                name="project_id"
                style={{ flex: 1 }}
              >
                <Select placeholder="选择项目" allowClear>
                  {projects.map((p) => (
                    <Option key={p.id} value={p.id}>
                      {p.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="浏览器"
                name="browser_type"
                style={{ width: 200 }}
              >
                <Select>
                  <Option value="chromium">Chromium</Option>
                  <Option value="firefox">Firefox</Option>
                  <Option value="webkit">WebKit</Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="无头模式"
                name="headless"
                valuePropName="checked"
              >
                <Switch checkedChildren="无头" unCheckedChildren="可见" />
              </Form.Item>
            </Space>

            {/* 步骤编辑 */}
            {editingScript && (
              <>
                <Divider />
                <Title level={4}>步骤配置（从上到下依次执行）</Title>

                <Form.List
                  name="steps"
                  rules={[
                    {
                      validator: async (_, steps) => {
                        if (!steps || steps.length === 0) {
                          return Promise.reject(
                            new Error('请至少添加一个步骤'),
                          );
                        }
                      },
                    },
                  ]}
                >
                  {(fields, { add, remove }) => (
                    <>
                      {fields.map((field, index) => (
                        <Card
                          key={field.key}
                          size="small"
                          style={{ marginBottom: 12 }}
                          title={`步骤 ${index + 1}`}
                          extra={
                            <Button
                              size="small"
                              danger
                              onClick={() => remove(field.name)}
                            >
                              删除
                            </Button>
                          }
                        >
                          <Space
                            direction="vertical"
                            style={{ width: '100%' }}
                            size="small"
                          >
                            <Space style={{ display: 'flex' }} align="baseline">
                              <Form.Item
                                {...field}
                                name={[field.name, 'action_type']}
                                fieldKey={[field.fieldKey, 'action_type']}
                                label="操作类型"
                                rules={[{ required: true, message: '请选择操作类型' }]}
                                style={{ width: 220 }}
                              >
                                <Select>
                                  {Object.entries(ACTION_LABELS).map(
                                    ([value, label]) => (
                                      <Option key={value} value={value}>
                                        {label}
                                      </Option>
                                    ),
                                  )}
                                </Select>
                              </Form.Item>

                              <Form.Item
                                {...field}
                                name={[field.name, 'description']}
                                fieldKey={[field.fieldKey, 'description']}
                                label="步骤说明"
                                style={{ flex: 1 }}
                              >
                                <Input placeholder="给这个步骤起个好理解的说明，方便别人看" />
                              </Form.Item>
                            </Space>

                            <Space style={{ display: 'flex' }} align="baseline">
                              <Form.Item
                                {...field}
                                name={[field.name, 'locator_type']}
                                fieldKey={[field.fieldKey, 'locator_type']}
                                label="元素定位类型"
                                style={{ width: 200 }}
                              >
                                <Select allowClear placeholder="不需要元素可留空">
                                  <Option value="id">ID</Option>
                                  <Option value="name">Name</Option>
                                  <Option value="css">CSS 选择器</Option>
                                  <Option value="xpath">XPath</Option>
                                  <Option value="text">文本</Option>
                                  <Option value="testid">data-testid</Option>
                                  <Option value="role">Role</Option>
                                  <Option value="label">Label 文本</Option>
                                </Select>
                              </Form.Item>

                              <Form.Item
                                {...field}
                                name={[field.name, 'locator_value']}
                                fieldKey={[field.fieldKey, 'locator_value']}
                                label="元素值"
                                style={{ flex: 1 }}
                              >
                                <Input placeholder="例如：#login-button 或 .btn-primary" />
                              </Form.Item>

                            </Space>

                            {/* 针对不同操作类型显示不同参数字段 */}
                            <Form.Item
                              noStyle
                              shouldUpdate={(prev, cur) =>
                                prev.steps?.[field.name]?.action_type !==
                                cur.steps?.[field.name]?.action_type
                              }
                            >
                              {({ getFieldValue }) => {
                                const currentAction =
                                  getFieldValue(['steps', field.name, 'action_type']);

                                if (currentAction === 'navigate') {
                                  return (
                                    <Form.Item
                                      {...field}
                                      name={[field.name, 'url']}
                                      fieldKey={[field.fieldKey, 'url']}
                                      label="URL"
                                      rules={[
                                        { required: true, message: '请输入要打开的地址' },
                                      ]}
                                    >
                                      <Input placeholder="例如：https://example.com/login" />
                                    </Form.Item>
                                  );
                                }

                                if (
                                  currentAction === 'fill' ||
                                  currentAction === 'select'
                                ) {
                                  return (
                                    <Form.Item
                                      {...field}
                                      name={[field.name, 'value']}
                                      fieldKey={[field.fieldKey, 'value']}
                                      label="输入/选择的值"
                                    >
                                      <Input placeholder="例如：test_user 或 选项值" />
                                    </Form.Item>
                                  );
                                }

                                if (currentAction === 'wait') {
                                  return (
                                    <Space
                                      style={{ display: 'flex' }}
                                      align="baseline"
                                    >
                                      <Form.Item
                                        {...field}
                                        name={[field.name, 'wait_type']}
                                        fieldKey={[field.fieldKey, 'wait_type']}
                                        label="等待方式"
                                        initialValue="timeout"
                                        style={{ width: 200 }}
                                      >
                                        <Select>
                                          <Option value="timeout">固定时间</Option>
                                          <Option value="selector">直到元素出现</Option>
                                          <Option value="navigation">页面加载完成</Option>
                                        </Select>
                                      </Form.Item>

                                      <Form.Item
                                        noStyle
                                        shouldUpdate={(prev, cur) =>
                                          prev.steps?.[field.name]?.wait_type !==
                                          cur.steps?.[field.name]?.wait_type
                                        }
                                      >
                                        {({ getFieldValue: gf }) => {
                                          const wt = gf([
                                            'steps',
                                            field.name,
                                            'wait_type',
                                          ]);
                                          if (wt === 'timeout' || !wt) {
                                            return (
                                              <Form.Item
                                                {...field}
                                                name={[field.name, 'timeout']}
                                                fieldKey={[field.fieldKey, 'timeout']}
                                                label="等待毫秒数"
                                                initialValue={5000}
                                              >
                                                <Input
                                                  type="number"
                                                  min={0}
                                                  placeholder="例如：5000 （5秒）"
                                                />
                                              </Form.Item>
                                            );
                                          }
                                          if (wt === 'selector') {
                                            return (
                                              <Form.Item
                                                {...field}
                                                name={[
                                                  field.name,
                                                  'wait_selector',
                                                ]}
                                                fieldKey={[
                                                  field.fieldKey,
                                                  'wait_selector',
                                                ]}
                                                label="等待的选择器"
                                              >
                                                <Input placeholder="例如：.loaded 或 #ready" />
                                              </Form.Item>
                                            );
                                          }
                                          return null;
                                        }}
                                      </Form.Item>
                                    </Space>
                                  );
                                }

                                if (currentAction === 'screenshot') {
                                  return (
                                    <Form.Item
                                      {...field}
                                      name={[field.name, 'screenshotName']}
                                      fieldKey={[
                                        field.fieldKey,
                                        'screenshotName',
                                      ]}
                                      label="截图名称（可选）"
                                    >
                                      <Input placeholder="例如：login-page" />
                                    </Form.Item>
                                  );
                                }

                                if (currentAction === 'assert') {
                                  return (
                                    <Space
                                      style={{ display: 'flex' }}
                                      align="baseline"
                                    >
                                      <Form.Item
                                        {...field}
                                        name={[field.name, 'assert_type']}
                                        fieldKey={[
                                          field.fieldKey,
                                          'assert_type',
                                        ]}
                                        label="断言类型"
                                        initialValue="text"
                                        style={{ width: 200 }}
                                      >
                                        <Select>
                                          <Option value="text">文本包含</Option>
                                          <Option value="url">URL 包含</Option>
                                          <Option value="visible">
                                            元素可见/不可见
                                          </Option>
                                        </Select>
                                      </Form.Item>
                                      <Form.Item
                                        {...field}
                                        name={[field.name, 'expected_value']}
                                        fieldKey={[
                                          field.fieldKey,
                                          'expected_value',
                                        ]}
                                        label="期望值"
                                      >
                                        <Input placeholder="例如：欢迎回来 / /dashboard" />
                                      </Form.Item>
                                    </Space>
                                  );
                                }

                                if (currentAction === 'extract') {
                                  return (
                                    <Space
                                      style={{ display: 'flex' }}
                                      align="baseline"
                                    >
                                      <Form.Item
                                        {...field}
                                        name={[field.name, 'variable_name']}
                                        fieldKey={[
                                          field.fieldKey,
                                          'variable_name',
                                        ]}
                                        label="变量名"
                                      >
                                        <Input placeholder="例如：loginToken" />
                                      </Form.Item>
                                      <Form.Item
                                        {...field}
                                        name={[field.name, 'attribute_name']}
                                        fieldKey={[
                                          field.fieldKey,
                                          'attribute_name',
                                        ]}
                                        label="属性名（可选）"
                                      >
                                        <Input placeholder="仅在从属性提取时使用，例如 value" />
                                      </Form.Item>
                                    </Space>
                                  );
                                }

                                return null;
                              }}
                            </Form.Item>
                          </Space>
                        </Card>
                      ))}

                      <Button
                        type="dashed"
                        block
                        onClick={() =>
                          add({
                            action_type: 'click',
                          })
                        }
                      >
                        + 添加步骤
                      </Button>
                    </>
                  )}
                </Form.List>
              </>
            )}
          </Form>
        )}
      </Modal>

      {/* 录制面板 */}
      <RecordingPanel
        visible={recordingPanelVisible}
        onClose={handleCloseRecordingPanel}
        onSave={handleRecordingSave}
      />

    </Space>
  );
};

export default UiTestManager;


