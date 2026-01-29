import React, { useReducer, useEffect, useCallback, useState, useMemo, memo } from 'react';
import axios from 'axios';
import apiClient from '../api/axios';
import { Row, Col, Card, Statistic, Progress, Typography, Space, notification, Tabs, Table, Tag, Button, Spin } from 'antd';
import ExecutionPieChart from './ExecutionPieChart';
import { testExecutionsAPI } from '../api/testExecutions';
import { uiTestsAPI } from '../api/uiTests';
import { EXECUTION_STATUS, EXECUTION_STATUS_COLORS } from '../constants';
import ExecutionLogModal from './ExecutionLogModal';
import '../css/TestReportList.css';

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
  
  // UI测试日志相关状态
  const [uiLogs, setUiLogs] = useState([]);
  const [uiLogsLoading, setUiLogsLoading] = useState(false);
  const [uiLogsPagination, setUiLogsPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  
  // 日志详情Modal相关状态
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [logType, setLogType] = useState('api'); // 'api' 或 'ui'
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

  // 获取UI测试日志列表
  const fetchUiTestLogs = useCallback(async (page = 1, pageSize = 20) => {
    setUiLogsLoading(true);
    try {
      const response = await testExecutionsAPI.getUiTestLogs({
        page,
        page_size: pageSize,
      });
      
      const { results, count } = response.data;
      setUiLogs(results || []);
      setUiLogsPagination(prev => ({
        ...prev,
        current: page,
        pageSize,
        total: count || 0,
      }));
    } catch (error) {
      if (!axios.isCancel(error)) {
        notification.error({ message: '获取UI测试日志失败', description: error.message });
      }
    } finally {
      setUiLogsLoading(false);
    }
  }, []);

  // 查看API测试详细日志
  const handleViewApiLog = async (record) => {
    setSelectedLog(record);
    setLogType('api');
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

  // 查看UI测试详细日志
  const handleViewUiLog = async (record) => {
    setSelectedLog(record);
    setLogType('ui');
    setLogModalVisible(true);
    setLogDetailLoading(true);
    setLogDetail(null);
    
    try {
      const response = await uiTestsAPI.getExecutionLogs(record.id);
      setLogDetail(response.data);
    } catch (error) {
      notification.error({ message: '获取日志详情失败', description: error.message });
    } finally {
      setLogDetailLoading(false);
    }
  };

  // 处理API测试日志分页变化
  const handleApiTableChange = (pagination) => {
    fetchApiTestLogs(pagination.current, pagination.pageSize);
  };

  // 处理UI测试日志分页变化
  const handleUiTableChange = (pagination) => {
    fetchUiTestLogs(pagination.current, pagination.pageSize);
  };

  // API测试日志表格列定义 - 使用useMemo优化
  const apiLogsColumns = useMemo(() => [
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
          [EXECUTION_STATUS.PASSED]: { color: 'success', text: '通过' },
          [EXECUTION_STATUS.FAILED]: { color: 'error', text: '失败' },
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
        <Button type="link" size="small" onClick={() => handleViewApiLog(record)}>
          查看日志
        </Button>
      ),
    },
  ], [handleViewApiLog]);

  // UI测试日志表格列定义 - 使用useMemo优化
  const uiLogsColumns = useMemo(() => [
    {
      title: '脚本名称',
      dataIndex: 'script_name',
      key: 'script_name',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '执行状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          [EXECUTION_STATUS.PASSED]: { color: 'success', text: '通过' },
          [EXECUTION_STATUS.FAILED]: { color: 'error', text: '失败' },
          [EXECUTION_STATUS.PENDING]: { color: 'default', text: '待执行' },
          [EXECUTION_STATUS.RUNNING]: { color: 'processing', text: '执行中' },
          skipped: { color: 'default', text: '跳过' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '执行人',
      dataIndex: 'executed_by_username',
      key: 'executed_by_username',
      width: 100,
    },
    {
      title: '执行时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewUiLog(record)}>
          查看日志
        </Button>
      ),
    },
  ], [handleViewUiLog]);

  return (
    <Space direction="vertical" size="large" className="test-report-container">
      <Title level={2}>测试报告</Title>

      <Tabs defaultActiveKey="statistics" onChange={(key) => {
        if (key === 'api-logs' && apiLogs.length === 0) {
          fetchApiTestLogs(1, 20);
        } else if (key === 'ui-logs' && uiLogs.length === 0) {
          fetchUiTestLogs(1, 20);
        }
      }}>
        <TabPane tab="测试统计" key="statistics">
          {loading && statistics.length === 0 ? (
            <Card loading={true} />
          ) : (
            statistics.map((stat, index) => (
              <Card key={index} title={`项目统计: ${stat.project_name}`} className="test-report-stat-card">
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
                <Row gutter={[16, 24]} className="test-report-stat-row">
                  <Col xs={24} md={8} className="test-report-progress-center">
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
              onChange={handleApiTableChange}
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="UI测试日志" key="ui-logs">
          <Card>
            <Table
              columns={uiLogsColumns}
              dataSource={uiLogs}
              loading={uiLogsLoading}
              rowKey="id"
              pagination={{
                current: uiLogsPagination.current,
                pageSize: uiLogsPagination.pageSize,
                total: uiLogsPagination.total,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
                pageSizeOptions: ['10', '20', '50', '100'],
              }}
              onChange={handleUiTableChange}
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 日志详情Modal */}
      {logDetailLoading ? (
        <div className="test-report-loading-center" style={{ position: 'fixed', top: '50%', left: '50%', zIndex: 1000 }}>
          <Spin size="large" />
        </div>
      ) : (
        <ExecutionLogModal
          visible={logModalVisible}
          onClose={() => {
            setLogModalVisible(false);
            setSelectedLog(null);
            setLogDetail(null);
            setLogType('api');
          }}
          title={logType === 'api' 
            ? `API测试执行日志 - ${selectedLog?.api_request_name || ''}` 
            : `UI测试执行日志 - ${selectedLog?.script_name || ''}`}
          executionType={logType}
          status={selectedLog?.status || 'pending'}
          totalCount={logType === 'ui' 
            ? (logDetail?.result_summary?.total_actions || 0) 
            : 1}
          passedCount={logType === 'ui' 
            ? (logDetail?.result_summary?.passed_actions || 0) 
            : (selectedLog?.status === 'passed' ? 1 : 0)}
          failedCount={logType === 'ui' 
            ? (logDetail?.result_summary?.failed_actions || 0) 
            : (selectedLog?.status === 'failed' ? 1 : 0)}
          executionDuration={logDetail?.execution_duration_ms 
            ? logDetail.execution_duration_ms / 1000 
            : logDetail?.response_time}
          responseStatus={logType === 'api' ? logDetail?.response_status : undefined}
          responseTime={logType === 'api' ? logDetail?.response_time : undefined}
          responseBody={logType === 'api' && logDetail?.api_response_data 
            ? JSON.stringify(logDetail.api_response_data) 
            : undefined}
          assertions={logType === 'api' ? logDetail?.assertions : undefined}
          screenshots={logType === 'ui' ? logDetail?.screenshots : undefined}
          logs={logDetail?.logs}
          errorMessage={logDetail?.error_message}
          startTime={selectedLog?.executed_at 
            ? new Date(selectedLog.executed_at).toLocaleString() 
            : selectedLog?.created_at 
            ? new Date(selectedLog.created_at).toLocaleString() 
            : undefined}
        />
      )}
    </Space>
  );
}

export default React.memo(TestReportList);