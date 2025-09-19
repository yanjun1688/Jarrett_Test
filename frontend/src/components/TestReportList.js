import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Row, Col, Card, Statistic, Progress, Table, Typography, Space, notification } from 'antd';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const { Title } = Typography;

function TestReportList() {
  const [reports, setReports] = useState([]);
  const [statistics, setStatistics] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = useCallback(async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/reports/');
      setReports(response.data.results || []);
    } catch (error) {
      notification.error({ message: '获取报告列表失败', description: error.message });
    }
  }, []);

  const fetchStatistics = useCallback(async () => {
    try {
      const projectsResponse = await axios.get('http://localhost:8000/api/projects/');
      if (projectsResponse.data.results && projectsResponse.data.results.length > 0) {
        // For simplicity, we still fetch stats for the first project as an example.
        // A more advanced implementation might have a selector to choose the project.
        const projectId = projectsResponse.data.results[0].id;
        const statsResponse = await axios.get(`http://localhost:8000/api/projects/${projectId}/statistics/`);
        setStatistics([statsResponse.data]);
      }
    } catch (error) {
      notification.error({ message: '获取统计信息失败', description: error.message });
    }
  }, []);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([fetchReports(), fetchStatistics()]);
      setLoading(false);
    };
    fetchAll();
  }, [fetchReports, fetchStatistics]);

  const reportColumns = [
    { title: '报告名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '通过率',
      dataIndex: 'pass_rate',
      key: 'pass_rate',
      render: (rate) => <Progress percent={parseFloat(rate)} size="small" />,
      width: 150,
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text) => new Date(text).toLocaleString() },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={2}>测试报告与统计</Title>

      {loading && statistics.length === 0 ? <Card loading={true} /> : statistics.map((stat, index) => (
        <Card key={index} title={`项目统计: ${stat.project_name}`}>
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
              <Title level={5}>执行结果分布</Title>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { name: '通过', value: stat.passed_executions },
                  { name: '失败', value: stat.failed_executions },
                  { name: '阻塞', value: stat.blocked_executions },
                  { name: '跳过', value: stat.skipped_executions }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </Col>
          </Row>
        </Card>
      ))}

      <Card title="报告列表">
        <Table
          columns={reportColumns}
          dataSource={reports}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 5 }}
        />
      </Card>
    </Space>
  );
}

export default TestReportList;
