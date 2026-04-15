/**
 * 响应时间分布图表组件
 * 展示压测结果中的响应时间分布和百分位数
 */
import React, { useMemo } from 'react';
import { Card, Row, Col, Statistic, Typography, Space } from 'antd';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
  AreaChart,
  Area,
  Cell
} from 'recharts';
import {
  ClockCircleOutlined,
  DashboardOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';

const { Text } = Typography;

/**
 * 响应时间分布图表组件
 * @param {Object} executionDetail - 执行详情数据
 * @param {Array} results - 原始请求结果数组 [{index, responseTime, success}]
 */
const ResponseTimeChart = ({ executionDetail, results = [] }) => {
  // 计算响应时间分布数据
  const distributionData = useMemo(() => {
    if (!results || results.length === 0) return [];
    
    const responseTimes = results
      .filter(r => r.responseTime)
      .map(r => r.responseTime)
      .sort((a, b) => a - b);
    
    if (responseTimes.length === 0) return [];
    
    // 分组统计（按响应时间区间）
    const buckets = {};
    const bucketSize = Math.ceil((Math.max(...responseTimes) - Math.min(...responseTimes)) / 10) || 10;
    
    responseTimes.forEach(time => {
      const bucket = Math.floor(time / bucketSize) * bucketSize;
      const bucketKey = `${bucket}-${bucket + bucketSize}`;
      buckets[bucketKey] = (buckets[bucketKey] || 0) + 1;
    });
    
    return Object.entries(buckets)
      .map(([range, count]) => ({
        range,
        count,
        label: `${range}ms`
      }))
      .sort((a, b) => parseInt(a.range.split('-')[0]) - parseInt(b.range.split('-')[0]));
  }, [results]);

  // 计算每个请求的响应时间趋势
  const trendData = useMemo(() => {
    if (!results || results.length === 0) return [];
    
    return results
      .filter(r => r.responseTime)
      .map((r, idx) => ({
        index: r.index || idx + 1,
        responseTime: r.responseTime,
        success: r.success
      }))
      .slice(0, 100); // 只展示前100个避免图表过于密集
  }, [results]);

  // 百分位数数据
  const percentileData = useMemo(() => {
    if (!executionDetail) return [];
    
    return [
      { name: 'P50', value: executionDetail.p50_response_time || 0, color: '#52c41a' },
      { name: 'P90', value: executionDetail.p90_response_time || 0, color: '#1890ff' },
      { name: 'P95', value: executionDetail.p95_response_time || 0, color: '#722ed1' },
      { name: 'P99', value: executionDetail.p99_response_time || 0, color: '#faad14' },
    ];
  }, [executionDetail]);

  // 无数据时显示
  if (!executionDetail && results.length === 0) {
    return (
      <Card>
        <Text type="secondary">暂无图表数据</Text>
      </Card>
    );
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 百分位数统计卡片 */}
      {executionDetail && (
        <Card title={<Space><DashboardOutlined /> 响应时间百分位数</Space>} size="small">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic 
                title={<Text style={{ color: '#52c41a' }}>P50</Text>}
                value={executionDetail.p50_response_time || 0}
                suffix="ms"
                valueStyle={{ color: '#52c41a', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title={<Text style={{ color: '#1890ff' }}>P90</Text>}
                value={executionDetail.p90_response_time || 0}
                suffix="ms"
                valueStyle={{ color: '#1890ff', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title={<Text style={{ color: '#722ed1' }}>P95</Text>}
                value={executionDetail.p95_response_time || 0}
                suffix="ms"
                valueStyle={{ color: '#722ed1', fontSize: 20 }}
              />
            </Col>
            <Col span={6}>
              <Statistic 
                title={<Text style={{ color: '#faad14' }}>P99</Text>}
                value={executionDetail.p99_response_time || 0}
                suffix="ms"
                valueStyle={{ color: '#faad14', fontSize: 20 }}
              />
            </Col>
          </Row>
          
          {/* 百分位数对比柱状图 */}
          <div style={{ marginTop: 16, height: 150 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={percentileData}>
                <XAxis dataKey="name" />
                <YAxis unit="ms" />
                <Tooltip formatter={(value) => `${value}ms`} />
                <Bar dataKey="value" fill="#1890ff">
                  {percentileData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 响应时间分布图 */}
      {distributionData.length > 0 && (
        <Card title={<Space><ClockCircleOutlined /> 响应时间分布</Space>} size="small">
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distributionData}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis label={{ value: '请求数', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Bar dataKey="count" fill="#1890ff" name="请求数" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* 响应时间趋势图 */}
      {trendData.length > 0 && (
        <Card title={<Space><ThunderboltOutlined /> 响应时间趋势 (前100个请求)</Space>} size="small">
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="index" label={{ value: '请求序号', position: 'insideBottom' }} />
                <YAxis unit="ms" />
                <Tooltip formatter={(value) => `${value}ms`} />
                {executionDetail?.avg_response_time && (
                  <ReferenceLine 
                    y={executionDetail.avg_response_time} 
                    stroke="#faad14" 
                    strokeDasharray="3 3"
                    label={{ value: '平均', fill: '#faad14' }}
                  />
                )}
                <Area 
                  type="monotone" 
                  dataKey="responseTime" 
                  stroke="#1890ff" 
                  fill="#1890ff" 
                  fillOpacity={0.3}
                  name="响应时间"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </Space>
  );
};

export default ResponseTimeChart;