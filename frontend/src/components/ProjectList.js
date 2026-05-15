import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  List, Button, Space, Modal, Form, Input, notification, Popconfirm,
  Drawer, Descriptions, Tag, Empty, Progress,
} from 'antd';
import {
  PlusOutlined,
  ProjectOutlined,
  ExperimentOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  BarChartOutlined,
  BookOutlined,
  FileTextOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { ProCard, StatisticCard } from '@ant-design/pro-components';
import { projectsAPI } from '../api/projects';
import StatsPieChart from './StatsPieChart';
import {
  transformPassRateData,
  transformProjectComposition,
  transformTestDistribution,
} from '../utils/chartTransformers';
import './ProjectList.css';

function ProjectList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [globalStats, setGlobalStats] = useState(null);
  const [projectStats, setProjectStats] = useState({});
  const [reportDrawerOpen, setReportDrawerOpen] = useState(false);
  const [reportProjectId, setReportProjectId] = useState(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await projectsAPI.getAll();
      setProjects(response.data.results || []);
    } catch (error) {
      console.error('获取项目列表失败:', error);
      notification.error({ message: '获取失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchGlobalStats = useCallback(async () => {
    try {
      const response = await projectsAPI.getGlobalStatistics();
      setGlobalStats(response.data.global);
    } catch (error) {
      console.error('获取全局统计失败:', error);
    }
  }, []);

  // 并发限制：一次最多 5 个请求
  const runConcurrent = async (items, fn, limit = 5) => {
    const results = [];
    for (let i = 0; i < items.length; i += limit) {
      const batch = items.slice(i, i + limit);
      const batchResults = await Promise.all(batch.map(fn));
      results.push(...batchResults);
    }
    return results;
  };

  useEffect(() => {
    if (projects.length === 0) return;

    let cancelled = false;
    const statsMap = {};
    (async () => {
      await runConcurrent(projects, async (project) => {
        try {
          const response = await projectsAPI.getProjectStatistics(project.id);
          statsMap[project.id] = response.data.projects?.[0];
        } catch (error) {
          // 静默失败
        }
      });
      if (!cancelled) {
        setProjectStats(statsMap);
      }
    })();
    return () => { cancelled = true; };
  }, [projects]);

  useEffect(() => {
    fetchProjects();
    fetchGlobalStats();
  }, [fetchProjects, fetchGlobalStats]);

  const openCreateModal = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEditModal = (project) => {
    setEditing(project);
    form.setFieldsValue({
      name: project.name,
      description: project.description,
    });
    setModalOpen(true);
  };

  const handleDelete = async (projectId) => {
    try {
      await projectsAPI.delete(projectId);
      notification.success({ message: '项目已删除' });
      fetchProjects();
    } catch (error) {
      notification.error({ message: '删除失败', description: error.message });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await projectsAPI.patch(editing.id, values);
        notification.success({ message: '项目已更新' });
      } else {
        await projectsAPI.create(values);
        notification.success({ message: '项目已创建' });
      }
      setModalOpen(false);
      fetchProjects();
    } catch (error) {
      notification.error({ message: '保存失败', description: error.message });
    }
  };

  const renderGlobalStats = () => {
    if (!globalStats) return null;

    const numberCards = [
      { title: '项目总数', value: globalStats.total_projects, icon: <ProjectOutlined /> },
      { title: '测试用例', value: globalStats.total_testcases, icon: <ExperimentOutlined /> },
      { title: '测试脚本', value: globalStats.total_scripts || 0, icon: <CodeOutlined /> },
      { title: '知识库', value: globalStats.total_knowledge_bases || 0, icon: <BookOutlined /> },
      { title: '知识文档', value: globalStats.total_documents || 0, icon: <FileTextOutlined /> },
      { title: '总执行次数', value: globalStats.total_executions, icon: <PlayCircleOutlined /> },
    ];

    const passRateData = transformPassRateData(globalStats);
    const assetData = transformProjectComposition(globalStats);

    return (
      <ProCard gutter={16} style={{ marginBottom: 24 }}>
        <ProCard colSpan="50%">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {numberCards.map((item, index) => (
              <StatisticCard
                key={index}
                statistic={{
                  value: item.value,
                  icon: <span style={{ fontSize: 20, color: '#1677ff' }}>{item.icon}</span>,
                  description: item.title,
                  layout: 'vertical',
                }}
              />
            ))}
          </div>
        </ProCard>
        <ProCard colSpan="50%">
          <ProCard split="vertical" gutter={12}>
            <ProCard colSpan="50%">
              <StatsPieChart
                data={passRateData}
                height={180}
                title="总体通过率"
                centerLabel={`${globalStats.pass_rate}%`}
                compact
              />
            </ProCard>
            <ProCard colSpan="50%">
              <StatsPieChart
                data={assetData}
                height={180}
                title="资产分布"
                compact
              />
            </ProCard>
          </ProCard>
        </ProCard>
      </ProCard>
    );
  };

  const renderProjectCard = (project) => {
    const stats = projectStats[project.id];

    return (
      <ProCard
        title={
          <Space>
            <ProjectOutlined style={{ color: '#1677ff' }} />
            <span style={{ fontWeight: 500 }}>{project.name}</span>
          </Space>
        }
        extra={
          <Space size={4}>
            <Button
              type="primary"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              详情
            </Button>
            <Button
              size="small"
              icon={<BarChartOutlined />}
              onClick={() => {
                setReportProjectId(project.id);
                setReportDrawerOpen(true);
              }}
            >
              报告
            </Button>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEditModal(project)}
            />
            <Popconfirm title="确认删除此项目？" onConfirm={() => handleDelete(project.id)}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        }
        headerBordered
        style={{ marginBottom: 16 }}
      >
        {project.description && (
          <p style={{ color: '#666', marginTop: 0, marginBottom: 16, fontSize: 14 }}>
            {project.description}
          </p>
        )}

        {stats && (
          <ProCard split="vertical" gutter={16}>
            <ProCard colSpan="35%">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px' }}>
                <div>
                  <div style={{ color: '#888', fontSize: 12 }}>测试用例</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{stats.total_testcases || 0}</div>
                </div>
                <div>
                  <div style={{ color: '#888', fontSize: 12 }}>测试脚本</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{stats.total_scripts || 0}</div>
                </div>
                <div>
                  <div style={{ color: '#888', fontSize: 12 }}>知识库</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{stats.total_knowledge_bases || 0}</div>
                </div>
                <div>
                  <div style={{ color: '#888', fontSize: 12 }}>文档</div>
                  <div style={{ fontSize: 20, fontWeight: 600 }}>{stats.total_documents || 0}</div>
                </div>
              </div>
            </ProCard>
            <ProCard colSpan="65%">
              <ProCard split="vertical" gutter={8}>
                <ProCard colSpan="33%">
                  <StatsPieChart
                    data={transformPassRateData(stats)}
                    height={130}
                    title="通过率"
                    centerLabel={`${stats.pass_rate}%`}
                    compact
                    showLegend={false}
                  />
                </ProCard>
                <ProCard colSpan="33%">
                  <StatsPieChart
                    data={transformProjectComposition(stats)}
                    height={130}
                    title="资产"
                    compact
                    showLegend={false}
                  />
                </ProCard>
                <ProCard colSpan="34%">
                  <StatsPieChart
                    data={transformTestDistribution(stats.detail)}
                    height={130}
                    title="类型"
                    compact
                    showLegend={false}
                  />
                </ProCard>
              </ProCard>
            </ProCard>
          </ProCard>
        )}
      </ProCard>
    );
  };

  return (
    <div className="project-workbench">
      <div className="header">
        <div>
          <h2>
            <ProjectOutlined style={{ marginRight: 8, color: '#1677ff' }} />
            项目工作台
          </h2>
          <div className="subtitle">管理和监控您的测试项目</div>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新增项目
        </Button>
      </div>

      {renderGlobalStats()}

      <div className="project-list-section">
        <div className="section-title">项目列表</div>

        <List
          loading={loading}
          dataSource={projects}
          renderItem={(project) => (
            <List.Item style={{ border: 'none', padding: 0 }}>
              {renderProjectCard(project)}
            </List.Item>
          )}
        />
      </div>

      <Drawer
        title={`项目报告 - ${
          projects.find((p) => p.id === reportProjectId)?.name || ''
        }`}
        placement="right"
        width={600}
        open={reportDrawerOpen}
        onClose={() => {
          setReportDrawerOpen(false);
          setReportProjectId(null);
        }}
      >
        {(() => {
          const stats = reportProjectId ? projectStats[reportProjectId] : null;
          if (!stats) {
            return <Empty description="暂无统计数据" />;
          }

          const passRateColor = stats.pass_rate >= 80 ? 'green'
            : stats.pass_rate >= 60 ? 'orange' : 'red';

          return (
            <div>
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="测试用例">{stats.total_testcases}</Descriptions.Item>
                <Descriptions.Item label="测试脚本">{stats.total_scripts ?? 0}</Descriptions.Item>
                <Descriptions.Item label="知识库">{stats.total_knowledge_bases ?? 0}</Descriptions.Item>
                <Descriptions.Item label="文档">{stats.total_documents ?? 0}</Descriptions.Item>
                <Descriptions.Item label="总执行次数">{stats.total_executions}</Descriptions.Item>
                <Descriptions.Item label="通过率">
                  <Tag color={passRateColor}>{stats.pass_rate}%</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="通过">{stats.passed_executions}</Descriptions.Item>
                <Descriptions.Item label="失败">{stats.failed_executions}</Descriptions.Item>
                <Descriptions.Item label="阻塞">{stats.blocked_executions}</Descriptions.Item>
                <Descriptions.Item label="跳过">{stats.skipped_executions}</Descriptions.Item>
              </Descriptions>

              {stats.detail && (
                <>
                  <div style={{ marginTop: 24, marginBottom: 12, fontWeight: 500 }}>按测试类型</div>
                  {Object.entries(stats.detail).map(([type, data]) => {
                    const total = data.total || 0;
                    const passed = data.passed || 0;
                    const percent = total > 0 ? Math.round((passed / total) * 100) : 0;
                    const typeLabels = {
                      feature: '功能测试',
                      api: 'API 测试',
                      script: '脚本测试',
                    };
                    return (
                      <div key={type} style={{ marginBottom: 12 }}>
                        <div style={{ marginBottom: 4 }}>{typeLabels[type] || type}</div>
                        <Progress
                          percent={percent}
                          format={() => `${passed}/${total}`}
                        />
                      </div>
                    );
                  })}
                </>
              )}
            </div>
          );
        })()}
      </Drawer>

      <Modal
        title={editing ? '编辑项目' : '新增项目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          preserve={false}
          initialValues={{ name: '', description: '' }}
        >
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input maxLength={100} showCount />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default ProjectList;
