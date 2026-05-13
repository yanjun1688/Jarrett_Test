import React from 'react';
import StatsPieChart from './StatsPieChart';
import { transformPassRateData } from '../utils/chartTransformers';

/**
 * @deprecated 请直接使用 StatsPieChart + transformPassRateData
 * 保留此组件以维持向后兼容（TestReportList.js 等依赖此组件）
 */
const ExecutionPieChart = ({ data, height = 300, title }) => {
  const chartData = React.useMemo(() => transformPassRateData(data), [data]);
  return (
    <StatsPieChart
      data={chartData}
      height={height}
      title={title}
      showLegend={true}
    />
  );
};

export default ExecutionPieChart;
