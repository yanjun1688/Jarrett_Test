import React, { useState } from 'react';
import { Card, Typography, Space, Button, Tag, Alert, message, Spin } from 'antd';
import { CopyOutlined, CheckCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { testGenerationAPI } from '../../api/testGeneration';
import ExecutionLogModal from '../ExecutionLogModal';

const { Text } = Typography;

const GenerationResult = ({ result, mode, onClear }) => {
  const [executing, setExecuting] = useState(false);
  const [execModalVisible, setExecModalVisible] = useState(false);
  const [execModalData, setExecModalData] = useState(null);

  if (!result) return null;

  if (result.error) {
    return (
      <Alert
        type="error"
        message="生成失败"
        description={result.error}
        showIcon
        closable
        onClose={onClear}
      />
    );
  }

  const handleCopy = () => {
    const content = result.markdown || result.code || result.analysis || '';
    navigator.clipboard.writeText(content);
    message.success('已复制到剪贴板');
  };

  const parseJsonFromResponse = (response) => {
    if (!response) return null;
    try {
      let jsonStr = response.trim();
      if (jsonStr.startsWith('```json')) {
        jsonStr = jsonStr.replace(/```json\s*/, '').replace(/```\s*$/, '');
      } else if (jsonStr.startsWith('```')) {
        jsonStr = jsonStr.replace(/```\s*/, '').replace(/```\s*$/, '');
      }
      return JSON.parse(jsonStr);
    } catch (e) {
      return null;
    }
  };

  const handleExecuteTest = async () => {
    if (!result.testType || result.testType !== 'api') {
      message.warning('仅支持执行API测试类型');
      return;
    }

    const jsonContent = result.markdown;
    const parsedJson = parseJsonFromResponse(jsonContent);
    if (!parsedJson) {
      message.error('无法解析JSON配置，请检查生成内容');
      return;
    }

    if (!result.projectId) {
      message.error('缺少项目ID');
      return;
    }

    setExecuting(true);
    setExecModalVisible(true);
    setExecModalData({
      status: 'running',
      totalCount: 1,
      passedCount: 0,
      failedCount: 0,
      logs: ['正在创建测试脚本...'],
    });

    try {
      const execResult = await testGenerationAPI.createAndExecuteScript(
        result.projectId,
        jsonContent
      );

      const isSuccess = execResult.success;
      const summary = execResult.summary || {};
      const logs = execResult.logs || [];
      const results = execResult.results || [];

      setExecModalData({
        status: isSuccess ? 'passed' : 'failed',
        totalCount: summary.total_steps || 1,
        passedCount: summary.passed || 0,
        failedCount: summary.failed || 0,
        executionDuration: results[0]?.elapsed ? `${results[0].elapsed.toFixed(2)}s` : undefined,
        logs: Array.isArray(logs) ? logs : [logs],
        responseStatus: results[0]?.status_code,
        responseTime: results[0]?.elapsed ? `${results[0].elapsed.toFixed(2)}s` : undefined,
        responseBody: results[0]?.response_data,
        assertions: results[0]?.assertion_results || [],
        errorMessage: execResult.error,
        startTime: new Date().toISOString(),
        endTime: new Date().toISOString(),
      });

      message[isSuccess ? 'success' : 'error']({
        message: isSuccess ? '测试执行通过' : '测试执行失败',
        description: `${summary.passed || 0}/${summary.total_steps || 1} 步骤通过`,
      });
    } catch (error) {
      setExecModalData({
        status: 'failed',
        totalCount: 1,
        passedCount: 0,
        failedCount: 1,
        logs: ['执行失败'],
        errorMessage: error.response?.data?.error || error.message || '执行失败',
      });
      message.error(error.response?.data?.error || error.message || '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const closeExecModal = () => {
    setExecModalVisible(false);
    setExecModalData(null);
  };

  const renderQualityScore = (score) => {
    if (!score) return null;
    const color = score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red';
    return <Tag color={color}>质量分: {score}</Tag>;
  };

  const isApiJsonResult = result.testType === 'api' && parseJsonFromResponse(result.markdown);

  return (
    <>
      <Card
        title={
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            <Text strong>生成结果</Text>
            {renderQualityScore(result.quality_score)}
            {isApiJsonResult && <Tag color="green">可直接执行</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Button icon={<CopyOutlined />} onClick={handleCopy}>
              复制内容
            </Button>
            {isApiJsonResult && (
              <Button
                icon={<PlayCircleOutlined />}
                type="primary"
                onClick={handleExecuteTest}
                loading={executing}
              >
                执行测试
              </Button>
            )}
            <Button onClick={onClear}>清除</Button>
          </Space>
        }
      >
        <Spin spinning={executing} tip="正在执行测试...">
          {isApiJsonResult ? (
            <div style={{
              padding: '16px',
              backgroundColor: '#f5f5f5',
              borderRadius: '4px',
            }}>
              <pre style={{
                backgroundColor: '#282c34',
                color: '#abb2bf',
                padding: '16px',
                borderRadius: '4px',
                overflow: 'auto',
                margin: 0,
              }}>
                <code>{JSON.stringify(parseJsonFromResponse(result.markdown), null, 2)}</code>
              </pre>
            </div>
          ) : (
            <div className="markdown-content" style={{
              padding: '16px',
            }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result.markdown || result.analysis || ''}
              </ReactMarkdown>
            </div>
          )}
        </Spin>
      </Card>

      <ExecutionLogModal
        visible={execModalVisible}
        onClose={closeExecModal}
        title="AI生成测试 - 执行结果"
        executionType="api"
        status={execModalData?.status || 'pending'}
        totalCount={execModalData?.totalCount || 0}
        passedCount={execModalData?.passedCount || 0}
        failedCount={execModalData?.failedCount || 0}
        executionDuration={execModalData?.executionDuration}
        logs={execModalData?.logs || []}
        responseStatus={execModalData?.responseStatus}
        responseTime={execModalData?.responseTime}
        responseBody={execModalData?.responseBody}
        assertionResults={execModalData?.assertions || []}
        errorMessage={execModalData?.errorMessage}
        startTime={execModalData?.startTime}
        endTime={execModalData?.endTime}
      />
    </>
  );
};

export default GenerationResult;
