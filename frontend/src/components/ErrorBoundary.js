import React from 'react';
import { Result, Button, Typography } from 'antd';
import logger from '../utils/logger';

const { Title, Paragraph } = Typography;

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // 更新 state 使下一次渲染能够显示降级后的 UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // 记录错误日志（会自动上报到错误监控服务）
    logger.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // 你可以自定义降级后的 UI 并渲染
      return (
        <Result
          status="error"
          title={<Title level={2}>出错了！</Title>}
          subTitle="抱歉，页面发生了错误。"
          extra={[
            <Button key="reload" type="primary" onClick={this.handleReload}>
              刷新页面
            </Button>,
            <Button key="home" onClick={this.handleGoHome}>
              返回首页
            </Button>,
          ]}
          style={{ marginTop: '100px' }}
        >
          <div style={{ textAlign: 'left', maxWidth: '800px', margin: '0 auto' }}>
            <Title level={4}>错误详情：</Title>
            <Paragraph>
              <strong>{this.state.error && this.state.error.toString()}</strong>
            </Paragraph>
            <Title level={4}>错误堆栈：</Title>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '16px',
                borderRadius: '4px',
                overflow: 'auto',
                maxHeight: '400px',
              }}
            >
              {this.state.errorInfo && this.state.errorInfo.componentStack}
            </pre>
          </div>
        </Result>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
