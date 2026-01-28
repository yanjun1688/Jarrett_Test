/**
 * Action类型图标映射
 */
import {
  CompassOutlined,
  ThunderboltOutlined,
  EditOutlined,
  SelectOutlined,
  AimOutlined,
  ClockCircleOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

// 使用字符串字面量以避免循环依赖（与 constants/index.js 中的 ACTION_TYPES 保持一致）
export const ACTION_ICONS = {
  navigate: CompassOutlined,
  click: ThunderboltOutlined, // 使用ThunderboltOutlined替代不存在的MouseOutlined
  fill: EditOutlined,
  select: SelectOutlined,
  hover: AimOutlined,
  wait: ClockCircleOutlined,
  screenshot: CameraOutlined,
  assert: CheckCircleOutlined,
  extract: DownloadOutlined,
};

export const ACTION_COLORS = {
  navigate: 'blue',
  click: 'green',
  fill: 'orange',
  select: 'purple',
  hover: 'cyan',
  wait: 'default',
  screenshot: 'red',
  assert: 'success',
  extract: 'geekblue',
};
