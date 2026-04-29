import React, { useState, useEffect } from 'react';
import { Card, Tabs, Typography, Space, Divider } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { projectsAPI } from '../../api/projects';
import ApiDefinitionForm from './ApiDefinitionForm';
import PrdUploadForm from './PrdUploadForm';
import GenerationResult from './GenerationResult';

const { Title, Text } = Typography;

const AiTestGenerator = () => {
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [generationResult, setGenerationResult] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState('api-definition');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const res = await projectsAPI.getAll();
      if (res.data?.results) {
        setProjects(res.data.results);
      } else if (Array.isArray(res.data)) {
        setProjects(res.data);
      }
    } catch (error) {
      console.error('加载项目失败:', error);
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleGenerationStart = () => {
    setGenerating(true);
    setGenerationResult(null);
  };

  const handleGenerationComplete = (result) => {
    setGenerating(false);
    setGenerationResult(result);
  };

  const handleGenerationError = (error) => {
    setGenerating(false);
    setGenerationResult({ error: error.message || '生成失败' });
  };

  const tabItems = [
    {
      key: 'api-definition',
      label: 'API定义',
      children: (
        <ApiDefinitionForm
          projects={projects}
          loadingProjects={loadingProjects}
          generating={generating}
          onGenerateStart={handleGenerationStart}
          onGenerateComplete={handleGenerationComplete}
          onGenerateError={handleGenerationError}
        />
      ),
    },
    {
      key: 'prd-upload',
      label: 'PRD文档',
      children: (
        <PrdUploadForm
          projects={projects}
          loadingProjects={loadingProjects}
          generating={generating}
          onGenerateStart={handleGenerationStart}
          onGenerateComplete={handleGenerationComplete}
          onGenerateError={handleGenerationError}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={3}>
              <RobotOutlined style={{ marginRight: 8 }} />
              AI 智能生成测试用例
            </Title>
            <Text type="secondary">
               通过API定义或PRD文档，智能生成测试脚本和用例
            </Text>
          </div>

          <Divider />

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
          />

          {generationResult && (
            <GenerationResult
              result={generationResult}
              mode={activeTab}
              onClear={() => setGenerationResult(null)}
            />
          )}
        </Space>
      </Card>
    </div>
  );
};

export default AiTestGenerator;