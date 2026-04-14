import React from 'react';
import { Card, Steps, Tag, Space } from 'antd';

const ExecutionFlowVisualization = ({ requests = [], extractRules = [] }) => {
  // 根据请求顺序生成steps数据 
  const steps = requests.map((request, index) => {
    const hasExtractRule = extractRules.some(rules => 
      rules && rules.length > 0 && extractRules[index] && extractRules[index].length > 0
    );
    
    return {
      title: (
        <div>
          <Space>
            <span>{request.name || '未知请求'}</span>
            {hasExtractRule && <Tag color="blue">提取变量</Tag>}
          </Space>
        </div>
      ),
      description: (
        <div>
          <div>方法: {request.method || 'GET'}</div>
          <div>路径: {request.url || '未设定'}</div>
        </div>
      )
    };
  });

  return (
    <Card title="执行流程可视化">
      <Steps
        items={steps}
        direction="vertical"
        size="small"
        progressDot
        current={steps.length} // 表示所有步骤都已完成设计
      />
      
      <div style={{ marginTop: 20 }}>
        <h4>执行说明</h4>
        <ul>
          <li>请求将按照上面的顺序依次执行</li>
          <li>标记"提取变量"的请求会尝试从响应中提取变量供后续请求使用</li>
          <li>在链式模式下，后续请求可以使用前述请求提取的变量</li>
        </ul>
      </div>
    </Card>
  );
};

export default ExecutionFlowVisualization;