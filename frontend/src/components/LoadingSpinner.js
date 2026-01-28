/**
 * 加载中组件 - 用于路由懒加载
 */
import { Spin } from 'antd';

const LoadingSpinner = () => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px',
      }}
    >
      <Spin size="large" tip="加载中..." />
    </div>
  );
};

export default LoadingSpinner;
