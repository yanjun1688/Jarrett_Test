/**
 * 应用常量配置
 */

// 浏览器类型
export const BROWSER_TYPES = {
  CHROMIUM: 'chromium',
  FIREFOX: 'firefox',
  WEBKIT: 'webkit',
};

// 浏览器类型显示名称
export const BROWSER_TYPE_LABELS = {
  [BROWSER_TYPES.CHROMIUM]: 'Chromium',
  [BROWSER_TYPES.FIREFOX]: 'Firefox',
  [BROWSER_TYPES.WEBKIT]: 'WebKit',
};

// Action类型（MVP只支持三种）
export const ACTION_TYPES = {
  NAVIGATE: 'navigate',
  CLICK: 'click',
  FILL: 'fill',
};

// Action类型中文标签
export const ACTION_LABELS = {
  [ACTION_TYPES.NAVIGATE]: '打开页面',
  [ACTION_TYPES.CLICK]: '点击',
  [ACTION_TYPES.FILL]: '输入内容',
};

// 执行状态
export const EXECUTION_STATUS = {
  PASSED: 'passed',
  FAILED: 'failed',
  RUNNING: 'running',
  PENDING: 'pending',
};

// 执行状态显示文本
export const EXECUTION_STATUS_LABELS = {
  [EXECUTION_STATUS.PASSED]: '通过',
  [EXECUTION_STATUS.FAILED]: '失败',
  [EXECUTION_STATUS.RUNNING]: '执行中',
  [EXECUTION_STATUS.PENDING]: '待执行',
};

// 执行模式
export const EXECUTION_MODES = {
  CHAIN: 'chain',
  SEQUENTIAL: 'sequential',
  CONCURRENT: 'concurrent',
};

// 默认配置值
export const DEFAULT_CONFIG = {
  VIEWPORT_WIDTH: 1280,
  VIEWPORT_HEIGHT: 720,
  TIMEOUT: 30000,
  HEADLESS: false,
  BROWSER_TYPE: BROWSER_TYPES.CHROMIUM,
  PAGE_SIZE: 10,
};

// 颜色映射
const COLOR_HEX_MAP = {
  blue: '#1890ff',
  green: '#52c41a',
  orange: '#fa8c16',
  purple: '#722ed1',
  cyan: '#13c2c2',
  default: '#d9d9d9',
  red: '#f5222d',
  success: '#52c41a',
  geekblue: '#2f54eb',
};

export const getColorHex = (colorName) => {
  return COLOR_HEX_MAP[colorName] || COLOR_HEX_MAP.default;
};
