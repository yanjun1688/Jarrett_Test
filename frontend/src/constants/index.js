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

// 执行状态颜色
export const EXECUTION_STATUS_COLORS = {
  [EXECUTION_STATUS.PASSED]: 'green',
  [EXECUTION_STATUS.FAILED]: 'red',
  [EXECUTION_STATUS.RUNNING]: 'processing',
  [EXECUTION_STATUS.PENDING]: 'default',
};

// 执行模式
export const EXECUTION_MODES = {
  CHAIN: 'chain',
  SEQUENTIAL: 'sequential',
  CONCURRENT: 'concurrent',
};

// 执行模式显示文本
export const EXECUTION_MODE_LABELS = {
  [EXECUTION_MODES.CHAIN]: '链式',
  [EXECUTION_MODES.SEQUENTIAL]: '顺序',
  [EXECUTION_MODES.CONCURRENT]: '并发',
};

// 执行模式颜色
export const EXECUTION_MODE_COLORS = {
  [EXECUTION_MODES.CHAIN]: '#722ed1',
  [EXECUTION_MODES.SEQUENTIAL]: '#52c41a',
  [EXECUTION_MODES.CONCURRENT]: '#1890ff',
};

// 定位器类型（MVP只支持四种）
export const LOCATOR_TYPES = {
  ID: 'id',
  NAME: 'name',
  CSS: 'css',
  TESTID: 'testid',
};

// 定位器类型选项
export const LOCATOR_TYPE_OPTIONS = [
  { value: LOCATOR_TYPES.ID, label: 'ID' },
  { value: LOCATOR_TYPES.NAME, label: 'Name' },
  { value: LOCATOR_TYPES.CSS, label: 'CSS 选择器' },
  { value: LOCATOR_TYPES.TESTID, label: 'data-testid' },
];

// 等待类型
export const WAIT_TYPES = {
  TIMEOUT: 'timeout',
  SELECTOR: 'selector',
  NAVIGATION: 'navigation',
};

// 等待类型选项
export const WAIT_TYPE_OPTIONS = [
  { value: WAIT_TYPES.TIMEOUT, label: '固定时间' },
  { value: WAIT_TYPES.SELECTOR, label: '直到元素出现' },
  { value: WAIT_TYPES.NAVIGATION, label: '页面加载完成' },
];

// 断言类型
export const ASSERT_TYPES = {
  TEXT: 'text',
  URL: 'url',
  VISIBLE: 'visible',
};

// 断言类型选项
export const ASSERT_TYPE_OPTIONS = [
  { value: ASSERT_TYPES.TEXT, label: '文本包含' },
  { value: ASSERT_TYPES.URL, label: 'URL 包含' },
  { value: ASSERT_TYPES.VISIBLE, label: '元素可见/不可见' },
];

// 提取类型
export const EXTRACT_TYPES = {
  TEXT: 'text',
  ATTRIBUTE: 'attribute',
};

// 默认配置值
export const DEFAULT_CONFIG = {
  VIEWPORT_WIDTH: 1280,
  VIEWPORT_HEIGHT: 720,
  TIMEOUT: 30000,
  HEADLESS: false,  // 默认关闭无头模式，方便用户看到浏览器执行过程
  BROWSER_TYPE: BROWSER_TYPES.CHROMIUM,
  PAGE_SIZE: 10,
};

// 颜色映射
export const COLOR_HEX_MAP = {
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

/**
 * 获取颜色十六进制值
 */
export const getColorHex = (colorName) => {
  return COLOR_HEX_MAP[colorName] || COLOR_HEX_MAP.default;
};

// 导出Action图标和颜色（从单独文件导入以避免循环依赖）
export { ACTION_ICONS, ACTION_COLORS } from './actionIcons';
