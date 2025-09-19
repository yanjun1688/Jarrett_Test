import React from 'react';
import { Layout, Menu } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  FileTextOutlined,
  PlaySquareOutlined,
  BarChartOutlined,
  CloudUploadOutlined,
  CodeOutlined,
  ApiOutlined,
  GroupOutlined,
} from '@ant-design/icons';
import { Link, Outlet, useLocation } from 'react-router-dom';
import './App.css';

const { Header, Content, Sider } = Layout;

const menuItems = [
  {
    key: '/',
    icon: <HomeOutlined />,
    label: <Link to="/">首页</Link>,
  },
  {
    key: '/projects',
    icon: <ProjectOutlined />,
    label: <Link to="/projects">项目管理</Link>,
  },
  {
    key: '/testcases',
    icon: <FileTextOutlined />,
    label: <Link to="/testcases">用例管理</Link>,
  },
  {
    key: '/executions',
    icon: <PlaySquareOutlined />,
    label: <Link to="/executions">测试执行</Link>,
  },
  {
    key: '/reports',
    icon: <BarChartOutlined />,
    label: <Link to="/reports">测试报告</Link>,
  },
  {
    key: '/import-export',
    icon: <CloudUploadOutlined />,
    label: <Link to="/import-export">导入导出</Link>,
  },
  {
    key: '/test-scripts',
    icon: <CodeOutlined />,
    label: <Link to="/test-scripts">测试脚本</Link>,
  },
  {
    key: '/api-tester',
    icon: <ApiOutlined />,
    label: <Link to="/api-tester">API测试</Link>,
  },
  {
    key: '/request-collections',
    icon: <GroupOutlined />,
    label: <Link to="/request-collections">请求集合</Link>,
  },
];

function App() {
  const location = useLocation();

  // Find the current selected key, handling nested routes
  const getSelectedKey = () => {
    const currentPath = location.pathname;
    // Find the key that is the best match for the start of the path
    const bestMatch = menuItems.map(item => item.key).sort((a, b) => b.length - a.length).find(key => currentPath.startsWith(key));
    return bestMatch || '/';
  };


  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: '32px', margin: '16px', background: 'rgba(255, 255, 255, 0.2)', borderRadius: '6px', color: 'white', textAlign: 'center', lineHeight: '32px' }}>
          JTest
        </div>
        <Menu theme="dark" selectedKeys={[getSelectedKey()]} mode="inline" items={menuItems} />
      </Sider>
      <Layout className="site-layout">
        <Header style={{ padding: '0 16px', background: '#fff' }} >
          <h2 style={{ margin: 0 }}>测试平台</h2>
        </Header>
        <Content style={{ margin: '16px' }}>
          <div style={{ padding: 24, minHeight: 'calc(100vh - 168px)', background: '#fff', borderRadius: '8px' }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
