import React, { useState } from 'react';
import logger from '../utils/logger';
import {
  Card,
  Upload,
  Button,
  Space,
  Typography,
  message,
  Spin,
  Empty,
} from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { processPRD } from '../api/aiAgent';
import ChatBotMessageRenderer from './ChatBotMessageRenderer';

const { Title, Paragraph } = Typography;

function AiTestCaseAnalysis() {
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState('');
  const [fileList, setFileList] = useState([]);

  // 处理文件上传和分析
  const handleProcessPRD = async (file) => {
    if (!file) {
      message.warning('请先选择文件');
      return;
    }

    setLoading(true);
    setAnalysisResult('');

    try {
      const response = await processPRD(file);

      if (response.success && response.data && response.data.analysis) {
        setAnalysisResult(response.data.analysis);
        message.success('PRD分析完成');
      } else {
        message.error('处理失败：未返回分析结果');
      }
    } catch (error) {
      logger.error('处理PRD失败:', error);
      message.error(
        error.response?.data?.error || error.message || '处理PRD文档失败，请检查文件格式和网络连接'
      );
    } finally {
      setLoading(false);
    }
  };

  // 文件上传配置
  const uploadProps = {
    accept: '.pdf,.doc,.docx,.txt',
    fileList,
    beforeUpload: (file) => {
      // 阻止自动上传
      return false;
    },
    onChange: (info) => {
      setFileList(info.fileList);
    },
    onRemove: () => {
      setFileList([]);
      setAnalysisResult('');
    },
    maxCount: 1,
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <FileTextOutlined style={{ marginRight: '8px' }} />
        AI分析用例
      </Title>
      <Paragraph type="secondary">
        上传PRD文档（PDF/Word/TXT），AI将自动分析并生成测试用例
      </Paragraph>


      <Card style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>选择PRD文档</Button>
            </Upload>
            <Button
              type="primary"
              size="large"
              icon={loading ? <LoadingOutlined /> : <CheckCircleOutlined />}
              onClick={() => {
                const file = fileList[0]?.originFileObj;
                if (file) {
                  handleProcessPRD(file);
                } else {
                  message.warning('请先选择文件');
                }
              }}
              loading={loading}
              disabled={loading || fileList.length === 0}
            >
              {loading ? 'AI分析中...' : '开始分析'}
            </Button>
          </Space>
        </Space>
      </Card>

      {loading && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Paragraph>AI正在分析PRD文档，请稍候...</Paragraph>
            </div>
          </div>
        </Card>
      )}

      {!loading && analysisResult && (
        <Card title="AI测试用例分析结果">
          <ChatBotMessageRenderer content={analysisResult} />
        </Card>
      )}

      {!loading && !analysisResult && fileList.length > 0 && (
        <Card>
          <Empty description="暂无分析结果，请点击'开始分析'按钮" />
        </Card>
      )}
    </div>
  );
}

export default AiTestCaseAnalysis;
