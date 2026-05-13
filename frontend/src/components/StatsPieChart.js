import React from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';

const StatsPieChart = ({
  data,
  height = 200,
  title,
  showLegend = true,
  compact = false,
}) => {
  const total = React.useMemo(
    () => data.reduce((sum, item) => sum + item.value, 0),
    [data]
  );

  const formatTooltip = (value, name) => {
    const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
    return [`${value} (${percent}%)`, name];
  };

  const formatLegend = (value) => {
    const item = data.find(d => d.name === value);
    if (!item) return value;
    const pct = total > 0 ? ((item.value / total) * 100).toFixed(1) : 0;
    return compact ? `${value} ${pct}%` : `${value}: ${item.value} (${pct}%)`;
  };

  if (!data || data.length === 0 || total === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#999', fontSize: compact ? 12 : 14 }}>暂无数据</span>
      </div>
    );
  }

  const outerRadius = compact ? '70%' : '75%';

  return (
    <div>
      {title && (
        <div style={{
          textAlign: 'center',
          marginBottom: compact ? 4 : 8,
          fontSize: compact ? 13 : 15,
          fontWeight: 500,
        }}>
          {title}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={outerRadius}
            isAnimationActive={true}
          >
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.color}
                stroke="#fff"
                strokeWidth={compact ? 1 : 2}
              />
            ))}
          </Pie>
          <Tooltip formatter={formatTooltip} />
          {showLegend && (
            <Legend
              verticalAlign="bottom"
              height={compact ? 24 : 36}
              formatter={formatLegend}
              wrapperStyle={{ fontSize: compact ? 11 : 13 }}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StatsPieChart;
