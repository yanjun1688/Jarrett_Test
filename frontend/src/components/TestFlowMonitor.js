import React, { useState, useEffect } from 'react';
import { Card, Spin, Alert, Statistic, Row, Col, List } from 'antd';
import { LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { testFlowAPI } from '../api';
import { useParams } from 'react-router-dom';

const TestFlowMonitor = () => {
  const { id } = useParams();
  const [executionData, setExecutionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchExecutionData = async () => {
      try {
        const response = await testFlowAPI.getFlowExecution(id);
        if (response.success) {
          setExecutionData(response.data);
        } else {
          setError(response.message || '获取执行数据失败');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchExecutionData();
    const interval = setInterval(fetchExecutionData, 5000);

    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }

  if (error) {
    return (
      <Alert message="错误" description={error} type="error" showIcon />
    );
  }

  if (!executionData) {
    return (
      <Alert message="没有找到执行数据" type="warning" showIcon />
    );
  }

  const { success, metrics, errors, node_results } = executionData;

  return (
    <div>
      <Card title="执行概览">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="节点总数"
              value={metrics.nodes_executed}
              prefix={success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="成功节点"
              value={metrics.successful_nodes}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="失败节点"
              value={metrics.failed_nodes}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="执行时间"
              value={metrics.duration}
              suffix="秒"
            />
          </Col>
        </Row>
      </Card>

      {errors.length > 0 && (
        <Card title="错误信息" type="error" style={{ marginTop: 16 }}>
          {errors.map((error, index) => (
            <div key={index} style={{ marginBottom: 8 }}>
              <strong>{error.node_name}:</strong> {error.error}
            </div>
          ))}
        </Card>
      )}

      <Card title="节点执行结果" style={{ marginTop: 16 }}>
        <List
          dataSource={Object.entries(node_results)}
          renderItem={([nodeId, result]) => (
            <List.Item key={nodeId} style={{ marginBottom: 16, padding: 12, border: '1px solid #f0f0f0', borderRadius: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong>Node {nodeId}</strong>
                {result.success ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                )}
              </div>
              {result.data && (
                <div style={{ fontSize: '12px', color: '#666', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(result.data, null, 2)}
                </div>
              )}
              {result.error && (
                <div style={{ fontSize: '12px', color: '#ff4d4f' }}>
                  {result.error}
                </div>
              )}
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default TestFlowMonitor;
