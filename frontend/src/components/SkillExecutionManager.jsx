import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Button,
  Input,
  List,
  Card,
  Space,
  Typography,
  Alert,
  message,
  Tag,
  Popconfirm,
  Drawer,
  Select,
  DatePicker,
  Table,
  Tooltip,
  Empty,
  Divider
} from 'antd';
import {
  SearchOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  ToolOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  CodeOutlined
} from '@ant-design/icons';
import { skillExecutionAPI } from '../api/skillExecution';
import moment from 'moment';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

/**
 * Skill 执行管理组件
 * 提供 Skill 搜索、执行和记录管理功能
 */
const SkillExecutionManager = ({
  visible,
  onCancel,
  onSuccess
}) => {
  // 步骤状态: 'search' | 'execute' | 'history'
  const [currentStep, setCurrentStep] = useState('search');
  const [loading, setLoading] = useState(false);
  
  // 搜索状态
  const [searchSite, setSearchSite] = useState('skill.sh');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [skills, setSkills] = useState([]);
  const [selectedSkill, setSelectedSkill] = useState(null);
  
  // 执行状态
  const [naturalLanguageInput, setNaturalLanguageInput] = useState('');
  const [executionParams, setExecutionParams] = useState('{}');
  const [executing, setExecuting] = useState(false);
  
  // 历史记录状态
  const [executions, setExecutions] = useState([]);
  const [executionDetail, setExecutionDetail] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [filters, setFilters] = useState({
    status: undefined,
    skill_name: undefined,
    created_at_from: undefined,
    created_at_to: undefined
  });
  
  // 分页
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 加载执行记录
  const loadExecutions = useCallback(async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      const params = {
        page,
        ...filters
      };
      const response = await skillExecutionAPI.getSkillExecutions(params);
      if (response.data?.success) {
        setExecutions(response.data.data?.results || response.data.data || []);
        setPagination({
          current: page,
          pageSize,
          total: response.data.data?.count || response.data.data?.length || 0
        });
      }
    } catch (error) {
      message.error('加载执行记录失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 搜索 Skill
  const handleSearchSkills = async () => {
    if (!searchSite.trim()) {
      message.warning('请输入 Skill 站点 URL');
      return;
    }
    
    setLoading(true);
    try {
      const response = await skillExecutionAPI.searchSkills(searchSite, searchKeyword);
      if (response.data?.success) {
        setSkills(response.data.data?.skills || []);
        if (response.data.data?.skills?.length === 0) {
          message.info('未找到匹配的 Skill');
        }
      }
    } catch (error) {
      message.error('搜索 Skill 失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 选择 Skill
  const handleSelectSkill = (skill) => {
    setSelectedSkill(skill);
    setCurrentStep('execute');
    // 预填充自然语言输入
    if (skill.description) {
      setNaturalLanguageInput(`使用 ${skill.name} ${skill.description}`);
    }
  };

  // 执行 Skill
  const handleExecute = async () => {
    if (!selectedSkill) {
      message.warning('请先选择一个 Skill');
      return;
    }
    if (!naturalLanguageInput.trim()) {
      message.warning('请输入自然语言指令');
      return;
    }

    setExecuting(true);
    try {
      let params = {};
      try {
        params = JSON.parse(executionParams || '{}');
      } catch (e) {
        message.warning('执行参数 JSON 格式错误，将使用空对象');
      }

      const data = {
        skill_name: selectedSkill.name,
        skill_site: searchSite,
        natural_language_input: naturalLanguageInput,
        execution_params: params
      };

      const response = await skillExecutionAPI.createSkillExecution(data);
      if (response.data?.success) {
        message.success('Skill 执行成功');
        // 显示结果
        setExecutionDetail(response.data.data);
        setDetailVisible(true);
        // 刷新历史记录
        loadExecutions();
        // 重置
        setNaturalLanguageInput('');
        setExecutionParams('{}');
      }
    } catch (error) {
      message.error('执行失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setExecuting(false);
    }
  };

  // 删除执行记录
  const handleDelete = async (id) => {
    try {
      await skillExecutionAPI.deleteSkillExecution(id);
      message.success('删除成功');
      loadExecutions(pagination.current);
    } catch (error) {
      message.error('删除失败: ' + (error.response?.data?.error || error.message));
    }
  };

  // 查看详情
  const handleViewDetail = async (record) => {
    try {
      const response = await skillExecutionAPI.getSkillExecutionDetail(record.id);
      if (response.data?.success) {
        setExecutionDetail(response.data.data);
        setDetailVisible(true);
      }
    } catch (error) {
      message.error('加载详情失败: ' + (error.response?.data?.error || error.message));
    }
  };

  // 返回搜索
  const handleBackToSearch = () => {
    setCurrentStep('search');
    setSelectedSkill(null);
    setNaturalLanguageInput('');
  };

  // 状态标签渲染
  const renderStatusTag = (status) => {
    const statusMap = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待执行' },
      running: { color: 'processing', icon: <SyncOutlined spin />, text: '执行中' },
      success: { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
      failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' }
    };
    const config = statusMap[status] || statusMap.pending;
    return (
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定义
  const columns = [
    {
      title: 'Skill 名称',
      dataIndex: 'skill_name',
      key: 'skill_name',
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.skill_site}</Text>
        </Space>
      )
    },
    {
      title: '自然语言输入',
      dataIndex: 'natural_language_input',
      key: 'natural_language_input',
      ellipsis: true,
      width: 300
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: renderStatusTag
    },
    {
      title: '执行耗时',
      dataIndex: 'execution_duration',
      key: 'execution_duration',
      width: 100,
      render: (duration) => duration ? `${duration.toFixed(2)}s` : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time) => moment(time).format('YYYY-MM-DD HH:mm:ss')
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此记录吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ];

  // 渲染搜索步骤
  const renderSearchStep = () => (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input
            placeholder="输入 Skill 站点 URL (如: skill.sh)"
            value={searchSite}
            onChange={(e) => setSearchSite(e.target.value)}
            prefix={<CodeOutlined />}
            size="large"
          />
          <Input.Search
            placeholder="搜索关键词 (可选)"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onSearch={handleSearchSkills}
            enterButton={<><SearchOutlined /> 搜索 Skill</>}
            size="large"
            loading={loading}
          />
        </Space>
      </Card>

      {skills.length > 0 && (
        <List
          grid={{ gutter: 16, column: 2 }}
          dataSource={skills}
          renderItem={(skill) => (
            <List.Item>
              <Card
                hoverable
                onClick={() => handleSelectSkill(skill)}
                title={
                  <Space>
                    <ToolOutlined />
                    <Text strong>{skill.name}</Text>
                    {skill.version && <Tag size="small">v{skill.version}</Tag>}
                  </Space>
                }
                extra={<Button type="primary" size="small">选择</Button>}
              >
                <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                  {skill.description || '暂无描述'}
                </Paragraph>
                {skill.parameters && (
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>参数:</Text>
                    <div style={{ marginTop: 4 }}>
                      {Object.entries(skill.parameters).map(([key, config]) => (
                        <Tag key={key} size="small" style={{ marginBottom: 4 }}>
                          {key}: {config.type}
                          {config.required && <span style={{ color: 'red' }}>*</span>}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            </List.Item>
          )}
        />
      )}

      {skills.length === 0 && !loading && (
        <Empty description="请先搜索 Skill" />
      )}
    </div>
  );

  // 渲染执行步骤
  const renderExecuteStep = () => (
    <div>
      <Alert
        message={
          <Space>
            <ToolOutlined />
            <Text strong>已选择 Skill: {selectedSkill?.name}</Text>
          </Space>
        }
        description={selectedSkill?.description}
        type="info"
        showIcon
        action={
          <Button size="small" onClick={handleBackToSearch}>
            重新选择
          </Button>
        }
        style={{ marginBottom: 16 }}
      />

      <Card title="执行配置">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>自然语言指令:</Text>
            <TextArea
              placeholder="输入自然语言指令，例如: 测试 https://api.example.com 接口"
              value={naturalLanguageInput}
              onChange={(e) => setNaturalLanguageInput(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <Text strong>执行参数 (JSON):</Text>
            <TextArea
              placeholder='{"url": "https://api.example.com", "method": "GET"}'
              value={executionParams}
              onChange={(e) => setExecutionParams(e.target.value)}
              rows={4}
            />
          </div>

          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleExecute}
            loading={executing}
            size="large"
            block
          >
            执行 Skill
          </Button>
        </Space>
      </Card>

      <Divider />

      <Card title="历史记录">
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="状态过滤"
            allowClear
            style={{ width: 120 }}
            value={filters.status}
            onChange={(value) => setFilters({ ...filters, status: value })}
          >
            <Option value="pending">待执行</Option>
            <Option value="running">执行中</Option>
            <Option value="success">成功</Option>
            <Option value="failed">失败</Option>
          </Select>
          
          <Input
            placeholder="Skill 名称"
            value={filters.skill_name}
            onChange={(e) => setFilters({ ...filters, skill_name: e.target.value })}
            style={{ width: 150 }}
          />

          <RangePicker
            onChange={(dates) => {
              if (dates) {
                setFilters({
                  ...filters,
                  created_at_from: dates[0]?.format('YYYY-MM-DD'),
                  created_at_to: dates[1]?.format('YYYY-MM-DD')
                });
              } else {
                setFilters({
                  ...filters,
                  created_at_from: undefined,
                  created_at_to: undefined
                });
              }
            }}
          />

          <Button icon={<ReloadOutlined />} onClick={() => loadExecutions()}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={executions}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={(pageInfo) => loadExecutions(pageInfo.current, pageInfo.pageSize)}
          size="small"
        />
      </Card>
    </div>
  );

  // 组件挂载时加载历史记录
  useEffect(() => {
    if (visible) {
      loadExecutions();
    }
  }, [visible, loadExecutions]);

  return (
    <>
      <Modal
        title={
          <Space>
            <ToolOutlined />
            <span>Skill 执行管理</span>
          </Space>
        }
        open={visible}
        onCancel={onCancel}
        width={1000}
        footer={null}
        bodyStyle={{ maxHeight: '70vh', overflow: 'auto' }}
      >
        {currentStep === 'search' && renderSearchStep()}
        {currentStep === 'execute' && renderExecuteStep()}
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="执行详情"
        placement="right"
        width={600}
        onClose={() => setDetailVisible(false)}
        open={detailVisible}
      >
        {executionDetail && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card size="small" title="基本信息">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div><Text strong>Skill 名称:</Text> {executionDetail.skill_name}</div>
                <div><Text strong>站点:</Text> {executionDetail.skill_site}</div>
                <div><Text strong>状态:</Text> {renderStatusTag(executionDetail.status)}</div>
                <div><Text strong>执行耗时:</Text> {executionDetail.execution_duration ? `${executionDetail.execution_duration.toFixed(2)}s` : '-'}</div>
                <div><Text strong>创建时间:</Text> {moment(executionDetail.created_at).format('YYYY-MM-DD HH:mm:ss')}</div>
              </Space>
            </Card>

            <Card size="small" title="自然语言输入">
              <Text>{executionDetail.natural_language_input}</Text>
            </Card>

            {executionDetail.execution_params && Object.keys(executionDetail.execution_params).length > 0 && (
              <Card size="small" title="执行参数">
                <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                  {JSON.stringify(executionDetail.execution_params, null, 2)}
                </pre>
              </Card>
            )}

            {executionDetail.result_data && (
              <Card size="small" title="执行结果" style={{ borderColor: '#52c41a' }}>
                <pre style={{ background: '#f6ffed', padding: 8, borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
                  {JSON.stringify(executionDetail.result_data, null, 2)}
                </pre>
              </Card>
            )}

            {executionDetail.error_message && (
              <Card size="small" title="错误信息" style={{ borderColor: '#ff4d4f' }}>
                <Alert message={executionDetail.error_message} type="error" />
              </Card>
            )}
          </Space>
        )}
      </Drawer>
    </>
  );
};

export default SkillExecutionManager;
