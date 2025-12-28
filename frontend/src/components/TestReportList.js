import React, { useReducer, useEffect, useCallback, useState } from 'react';
import axios from 'axios';
import apiClient from '../api/axios';
import { Row, Col, Card, Statistic, Progress, Typography, Space, notification, Tabs, Table, Tag, Button, Modal, Descriptions, Spin } from 'antd';
import ExecutionPieChart from './ExecutionPieChart';
import { testExecutionsAPI } from '../api/testExecutions';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const initialState = {
  statistics: [],
  loading: true,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'FETCH_SUCCESS':
      return {
        ...state,
        loading: false,
        statistics: action.payload.statistics,
      };
    case 'FETCH_ERROR':
      return {
        ...state,
        loading: false,
        error: action.payload,
      };
    default:
      throw new Error();
  }
}

function TestReportList() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { statistics, loading } = state;
  
  // API测试日志相关状态
  const [apiLogs, setApiLogs] = useState([]);
  const [apiLogsLoading, setApiLogsLoading] = useState(false);
  const [apiLogsPagination, setApiLogsPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [logDetailLoading, setLogDetailLoading] = useState(false);
  const [logDetail, setLogDetail] = useState(null);

  const fetchData = useCallback(async (signal) => {
    try {
      const response = await apiClient.get('/report-data/', { signal });
      const statistics = response.data.statistics || [];
      dispatch({ type: 'FETCH_SUCCESS', payload: { statistics } });
    } catch (error) {
      if (!axios.isCancel(error)) {
        notification.error({ message: '获取数据失败', description: error.message });
        dispatch({ type: 'FETCH_ERROR', payload: error.message });
      }
    }
  }, []);

  useEffect(() => {
    const abortController = new AbortController();
    const { signal } = abortController;

    fetchData(signal);

    return () => {
      abortController.abort();
    };
  }, [fetchData]);

  // 获取API测试日志列表
  const fetchApiTestLogs = useCallback(async (page = 1, pageSize = 20) => {
    setApiLogsLoading(true);
    try {
      const response = await testExecutionsAPI.getApiTestLogs({
        page,
        page_size: pageSize,
      });
      
      const { results, count } = response.data;
      setApiLogs(results || []);
      setApiLogsPagination(prev => ({
        ...prev,
        current: page,
        pageSize,
        total: count || 0,
      }));
    } catch (error) {
      if (!axios.isCancel(error)) {
        notification.error({ message: '获取API测试日志失败', description: error.message });
      }
    } finally {
      setApiLogsLoading(false);
    }
  }, []);

  // 查看详细日志
  const handleViewLog = async (record) => {
    setSelectedLog(record);
    setLogModalVisible(true);
    setLogDetailLoading(true);
    setLogDetail(null);
    
    try {
      const response = await testExecutionsAPI.getAction(record.id, 'logs');
      setLogDetail(response.data);
    } catch (error) {
      notification.error({ message: '获取日志详情失败', description: error.message });
    } finally {
      setLogDetailLoading(false);
    }
  };

  // 处理分页变化
  const handleTableChange = (pagination) => {
    fetchApiTestLogs(pagination.current, pagination.pageSize);
  };

  // API测试日志表格列定义
  const apiLogsColumns = [
    {
      title: 'API名称',
      dataIndex: 'api_request_name',
      key: 'api_request_name',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '请求方法',
      dataIndex: 'api_request_method',
      key: 'api_request_method',
      width: 100,
      render: (method) => {
        const colors = {
          GET: 'blue',
          POST: 'green',
          PUT: 'orange',
          PATCH: 'purple',
          DELETE: 'red',
        };
        return <Tag color={colors[method] || 'default'}>{method}</Tag>;
      },
    },
    {
      title: '请求URL',
      dataIndex: 'api_request_url',
      key: 'api_request_url',
      ellipsis: true,
    },
    {
      title: '执行状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          passed: { color: 'success', text: '通过' },
          failed: { color: 'error', text: '失败' },
          pending: { color: 'default', text: '待执行' },
          blocked: { color: 'warning', text: '阻塞' },
          skipped: { color: 'default', text: '跳过' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '执行人',
      dataIndex: 'executor_name',
      key: 'executor_name',
      width: 100,
    },
    {
      title: '执行时间',
      dataIndex: 'executed_at',
      key: 'executed_at',
      width: 180,
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewLog(record)}>
          查看日志
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={2}>测试报告</Title>

      <Tabs defaultActiveKey="statistics" onChange={(key) => {
        if (key === 'api-logs' && apiLogs.length === 0) {
          fetchApiTestLogs(1, 20);
        }
      }}>
        <TabPane tab="测试统计" key="statistics">
          {loading && statistics.length === 0 ? (
            <Card loading={true} />
          ) : (
            statistics.map((stat, index) => (
              <Card key={index} title={`项目统计: ${stat.project_name}`} style={{ marginBottom: 16 }}>
                <Row gutter={[16, 24]}>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic title="总用例数" value={stat.total_testcases} />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic title="总执行数" value={stat.total_executions} />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic title="通过" value={stat.passed_executions} valueStyle={{ color: '#3f8600' }} />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <Statistic title="失败" value={stat.failed_executions} valueStyle={{ color: '#cf1322' }} />
                  </Col>
                </Row>
                <Row gutter={[16, 24]} style={{ marginTop: 24 }}>
                  <Col xs={24} md={8} style={{ textAlign: 'center' }}>
                    <Title level={5}>通过率</Title>
                    <Progress type="circle" percent={parseFloat(stat.pass_rate)} />
                  </Col>
                  <Col xs={24} md={16}>
                    <ExecutionPieChart
                      data={stat}
                      height={300}
                      title="执行结果分布"
                      showLabels={true}
                    />
                  </Col>
                </Row>
              </Card>
            ))
          )}
        </TabPane>
        
        <TabPane tab="API测试日志" key="api-logs">
          <Card>
            <Table
              columns={apiLogsColumns}
              dataSource={apiLogs}
              loading={apiLogsLoading}
              rowKey="id"
              pagination={{
                current: apiLogsPagination.current,
                pageSize: apiLogsPagination.pageSize,
                total: apiLogsPagination.total,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
                pageSizeOptions: ['10', '20', '50', '100'],
              }}
              onChange={handleTableChange}
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 日志详情Modal */}
      <Modal
        title="API测试执行日志详情"
        open={logModalVisible}
        onCancel={() => {
          setLogModalVisible(false);
          setSelectedLog(null);
          setLogDetail(null);
        }}
        footer={null}
        width={900}
        destroyOnClose
      >
        {selectedLog && (
          <div>
            <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="API名称">{selectedLog.api_request_name}</Descriptions.Item>
              <Descriptions.Item label="请求方法">
                <Tag color="blue">{selectedLog.api_request_method}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="请求URL" span={2}>
                <Text copyable>{selectedLog.api_request_url}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="执行状态">
                <Tag color={selectedLog.status === 'passed' ? 'success' : 'error'}>
                  {selectedLog.status === 'passed' ? '通过' : selectedLog.status === 'failed' ? '失败' : selectedLog.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="执行人">{selectedLog.executor_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="执行时间">
                {new Date(selectedLog.executed_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            {logDetailLoading ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <Spin size="large" />
              </div>
            ) : logDetail ? (
              <div>
                <Title level={5}>执行日志</Title>
                <div
                  style={{
                    backgroundColor: '#f5f5f5',
                    padding: '12px',
                    borderRadius: '4px',
                    maxHeight: '400px',
                    overflowY: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {logDetail.logs && logDetail.logs.length > 0 ? (
                    logDetail.logs.map((log, index) => (
                      <div key={index}>{log}</div>
                    ))
                  ) : (
                    <Text type="secondary">暂无日志</Text>
                  )}
                </div>

                {logDetail.api_response_data && (
                  <div style={{ marginTop: 16 }}>
                    <Title level={5}>响应数据</Title>
                    <div
                      style={{
                        backgroundColor: '#f5f5f5',
                        padding: '12px',
                        borderRadius: '4px',
                        maxHeight: '300px',
                        overflowY: 'auto',
                      }}
                    >
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {JSON.stringify(logDetail.api_response_data, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
      </Modal>
    </Space>
  );
}

export default React.memo(TestReportList);