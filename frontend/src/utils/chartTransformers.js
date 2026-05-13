export const CHART_COLORS = {
  passed: '#52c41a',
  failed: '#ff4d4f',
  blocked: '#faad14',
  skipped: '#8c8c8c',
  testcases: '#1677ff',
  scripts: '#722ed1',
  knowledgeBases: '#13c2c2',
  documents: '#fa8c16',
  functional: '#eb2f96',
  api: '#2f54eb',
  script: '#fadb14',
};

export const transformPassRateData = (stats) => {
  if (!stats) return [];
  return [
    { name: '通过', value: stats.passed_executions || 0, color: CHART_COLORS.passed },
    { name: '失败', value: stats.failed_executions || 0, color: CHART_COLORS.failed },
    { name: '阻塞', value: stats.blocked_executions || 0, color: CHART_COLORS.blocked },
    { name: '跳过', value: stats.skipped_executions || 0, color: CHART_COLORS.skipped },
  ].filter(item => item.value > 0);
};

export const transformProjectComposition = (stats) => {
  if (!stats) return [];
  return [
    { name: '测试用例', value: stats.total_testcases || 0, color: CHART_COLORS.testcases },
    { name: '测试脚本', value: stats.total_scripts || 0, color: CHART_COLORS.scripts },
    { name: '知识库', value: stats.total_knowledge_bases || 0, color: CHART_COLORS.knowledgeBases },
    { name: '文档', value: stats.total_documents || 0, color: CHART_COLORS.documents },
  ].filter(item => item.value > 0);
};

export const transformTestDistribution = (detail) => {
  if (!detail) return [];
  const labels = { feature: '功能测试', api: 'API测试', script: '脚本测试' };
  const colors = {
    feature: CHART_COLORS.functional,
    api: CHART_COLORS.api,
    script: CHART_COLORS.script,
  };
  return Object.entries(detail)
    .map(([type, data]) => ({
      name: labels[type] || type,
      value: data.total || 0,
      color: colors[type] || '#999',
    }))
    .filter(item => item.value > 0);
};
