import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { List, Card, Typography, Spin } from 'antd';
import { Link } from 'react-router-dom';

const { Title } = Typography;
const { Meta } = Card;

function ProjectList() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/projects/');
      setProjects(response.data.results || []);
    } catch (error) {
      console.error('获取项目列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return (
    <div style={{ width: '100%' }}>
      <Title level={2}>项目列表</Title>
      <List
        loading={loading}
        grid={{
          gutter: 16,
          xs: 1,
          sm: 2,
          md: 3,
          lg: 3,
          xl: 4,
          xxl: 4,
        }}
        dataSource={projects}
        renderItem={(project) => (
          <List.Item>
            <Link to={`/projects/${project.id}`}>
              <Card
                hoverable
                title={project.name}
              >
                <Meta
                  description={project.description || '暂无描述'}
                />
              </Card>
            </Link>
          </List.Item>
        )}
      />
    </div>
  );
}

export default ProjectList;
