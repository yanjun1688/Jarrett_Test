import React from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = {
  passed: '#52c41a',
  failed: '#ff4d4f',
  blocked: '#faad14',
  skipped: '#8c8c8c'
};

/**
 * 测试执行结果饼图组件
 *
 * 属性:
 * - data: 统计数据对象，包含 passed_executions, failed_executions 等字段
 * - height: 图表高度（默认 300）
 * - title: 图表标题
 * - showLabels: 是否显示标签（默认 true）
 */
const ExecutionPieChart = ({ data, height = 300, title, showLabels = true }) => {
  // 数据转换：将统计数据转换为饼图数据格式
  const chartData = React.useMemo(() => {
    if (!data) return [];

    const result = [
      { name: '通过', value: data.passed_executions || 0, color: COLORS.passed, key: 'passed' },
      { name: '失败', value: data.failed_executions || 0, color: COLORS.failed, key: 'failed' },
      { name: '阻塞', value: data.blocked_executions || 0, color: COLORS.blocked, key: 'blocked' },
      { name: '跳过', value: data.skipped_executions || 0, color: COLORS.skipped, key: 'skipped' }
    ].filter(item => item.value > 0); // 过滤为0的数据

    return result;
  }, [data]);

  // 计算总数
  const total = React.useMemo(() => {
    return chartData.reduce((sum, item) => sum + item.value, 0);
  }, [chartData]);

  // 格式化提示
  const formatTooltip = (value, name) => {
    const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
    return [`${value} (${percent}%)`, name];
  };

  // 格式化图例
  const formatLegend = (value) => {
    const item = chartData.find(d => d.name === value);
    if (!item) return value;
    const percent = total > 0 ? ((item.value / total) * 100).toFixed(1) : 0;
    return `${value}: ${item.value} (${percent}%)`;
  };

  // 自定义标签
  const renderLabel = (entry) => {
    if (!showLabels) return null;
    const percent = total > 0 ? ((entry.value / total) * 100).toFixed(1) : 0;
    return `${entry.name}: ${entry.value} (${percent}%)`;
  };

  if (!data || chartData.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#999' }}>暂无数据</span>
      </div>
    );
  }

  return (
    <div>
      {title && (
        <h4 style={{ textAlign: 'center', marginBottom: 16, fontWeight: 'normal' }}>
          {title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={Math.min(height / 3, 120)}
            label={renderLabel}
            labelLine={showLabels}
            isAnimationActive={true}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${entry.key}-${index}`} fill={entry.color} stroke="#fff" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip
            formatter={formatTooltip}
            contentStyle={{
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              padding: '8px 12px'
            }}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={formatLegend}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ExecutionPieChart;
