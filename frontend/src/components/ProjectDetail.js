import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../api/axios';
import TestCaseList from './TestCaseList';
import TestExecutionList from './TestExecutionList';
import { Descriptions, Tabs, Typography, Spin, Card, notification } from 'antd';

const { Title } = Typography;
const { TabPane } = Tabs;

function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProject = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/projects/${id}/`);
      setProject(response.data);
    } catch (error) {
      notification.error({ message: '获取项目详情失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: 50 }}><Spin size="large" /></div>;
  }

  if (!project) {
    return <Title level={3}>项目未找到</Title>;
  }

  return (
    <Card>
      <Descriptions title={<Title level={2}>{project.name}</Title>} bordered column={1}>
        <Descriptions.Item label="描述">{project.description || '暂无描述'}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{new Date(project.created_at).toLocaleString()}</Descriptions.Item>
      </Descriptions>

      <Tabs defaultActiveKey="1" style={{ marginTop: 24 }}>
        <TabPane tab="测试用例" key="1">
          <TestCaseList projectId={id} />
        </TabPane>
        <TabPane tab="测试执行记录" key="2">
          <TestExecutionList projectId={id} />
        </TabPane>
      </Tabs>
    </Card>
  );
}

export default ProjectDetail;
