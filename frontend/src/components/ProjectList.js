import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  List, Button, Space, Modal, Form, Input, notification, Popconfirm,
  Drawer, Descriptions, Tag, Empty, Divider,
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
import { ProCard } from '@ant-design/pro-components';
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
  const [drawerWidth, setDrawerWidth] = useState(640);
  const resizingRef = useRef(null);

  const fetchProjects = useCallback(async () => {
    const response = await projectsAPI.getAll();
    setProjects(response.data.results || []);
  }, []);

  const fetchAllStats = useCallback(async () => {
    const response = await projectsAPI.getStatistics();
    setGlobalStats(response.data.global);
    const statsMap = {};
    response.data.projects.forEach(stats => {
      statsMap[stats.project_id] = stats;
    });
    setProjectStats(statsMap);
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchProjects().catch((error) => {
        console.error('获取项目列表失败:', error);
        const msg = error.response?.data?.error || error.response?.data?.detail || (typeof error.message === 'string' ? error.message : '未知错误');
        notification.error({ message: '获取失败', description: msg });
      }),
      fetchAllStats().catch((error) => {
        console.error('获取统计失败:', error);
        const msg = error.response?.data?.error || error.response?.data?.detail || (typeof error.message === 'string' ? error.message : '未知错误');
        notification.error({ message: '获取统计失败', description: msg });
      }),
    ]).finally(() => setLoading(false));
  }, [fetchProjects, fetchAllStats]);

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

  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = drawerWidth;
    resizingRef.current = true;

    const handleMouseMove = (e) => {
      if (!resizingRef.current) return;
      const newWidth = Math.max(400, Math.min(1200, startWidth + (startX - e.clientX)));
      setDrawerWidth(newWidth);
    };

    const handleMouseUp = () => {
      resizingRef.current = null;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [drawerWidth]);

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
      <div className="stats-container">
        <div className="stats-left">
          <div className="stats-grid">
            {numberCards.map((item, index) => (
              <div className="stat-card" key={index}>
                <div className="stat-card-icon">{item.icon}</div>
                <div className="stat-card-value">{item.value}</div>
                <div className="stat-card-label">{item.title}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="stats-right">
          <div className="chart-wrap">
            <StatsPieChart data={passRateData} height={180} title="通过率" compact />
          </div>
          <div className="chart-wrap">
            <StatsPieChart data={assetData} height={180} title="项目构成" compact />
          </div>
        </div>
      </div>
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
          <p className="project-description">{project.description}</p>
        )}

        {stats && (
          <div className="project-stats-body">
            <div className="project-stats-numbers">
              <div className="project-stats-numbers-grid">
                <div>
                  <div className="stat-label">测试用例</div>
                  <div className="stat-value">{stats.total_testcases || 0}</div>
                </div>
                <div>
                  <div className="stat-label">测试脚本</div>
                  <div className="stat-value">{stats.total_scripts || 0}</div>
                </div>
                <div>
                  <div className="stat-label">知识库</div>
                  <div className="stat-value">{stats.total_knowledge_bases || 0}</div>
                </div>
                <div>
                  <div className="stat-label">文档</div>
                  <div className="stat-value">{stats.total_documents || 0}</div>
                </div>
              </div>
            </div>
            <div className="project-stats-charts">
              <div className="chart-wrap">
                <StatsPieChart data={transformPassRateData(stats)} height={130} title="通过率" compact />
              </div>
              <div className="chart-wrap">
                <StatsPieChart data={transformProjectComposition(stats)} height={130} title="构成" compact />
              </div>
              <div className="chart-wrap">
                <StatsPieChart data={transformTestDistribution(stats.detail)} height={130} title="测试分布" compact />
              </div>
            </div>
          </div>
        )}
      </ProCard>
    );
  };

  const drawerStats = reportProjectId ? projectStats[reportProjectId] : null;

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
        width={drawerWidth}
        open={reportDrawerOpen}
        onClose={() => {
          setReportDrawerOpen(false);
          setReportProjectId(null);
        }}
      >
        <div className="resize-handle" onMouseDown={handleResizeStart} />
        {drawerStats ? (
          <div>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="测试用例">{drawerStats.total_testcases}</Descriptions.Item>
              <Descriptions.Item label="测试脚本">{drawerStats.total_scripts ?? 0}</Descriptions.Item>
              <Descriptions.Item label="知识库">{drawerStats.total_knowledge_bases ?? 0}</Descriptions.Item>
              <Descriptions.Item label="文档">{drawerStats.total_documents ?? 0}</Descriptions.Item>
              <Descriptions.Item label="总执行次数">{drawerStats.total_executions}</Descriptions.Item>
              <Descriptions.Item label="通过率">
                <Tag color={
                  drawerStats.pass_rate >= 80 ? 'green'
                    : drawerStats.pass_rate >= 60 ? 'orange' : 'red'
                }>{drawerStats.pass_rate}%</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="通过">{drawerStats.passed_executions}</Descriptions.Item>
              <Descriptions.Item label="失败">{drawerStats.failed_executions}</Descriptions.Item>
              <Descriptions.Item label="阻塞">{drawerStats.blocked_executions}</Descriptions.Item>
              <Descriptions.Item label="跳过">{drawerStats.skipped_executions}</Descriptions.Item>
            </Descriptions>

            {drawerStats.detail && (
              <>
                <Divider>数据概览</Divider>
                <div className="drawer-charts">
                  <div className="chart-wrap">
                    <StatsPieChart data={transformPassRateData(drawerStats)} height={200} title="通过率" />
                  </div>
                  <div className="chart-wrap">
                    <StatsPieChart data={transformProjectComposition(drawerStats)} height={200} title="项目构成" />
                  </div>
                  <div className="chart-wrap">
                    <StatsPieChart data={transformTestDistribution(drawerStats.detail)} height={200} title="测试分布" />
                  </div>
                </div>
              </>
            )}
          </div>
        ) : (
          <Empty description="暂无统计数据" />
        )}
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
