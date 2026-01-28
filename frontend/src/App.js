import React from 'react';
import { Layout, Menu, Dropdown, Avatar, Space, Button, message } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  FileTextOutlined,
  PlaySquareOutlined,
  BarChartOutlined,
  CodeOutlined,
  ApiOutlined,
  GroupOutlined,
  UserOutlined,
  LogoutOutlined,
  RobotOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import MemberManager from './components/MemberManager';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { useNavigate } from 'react-router-dom';
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
    key: '/api-tester',
    icon: <ApiOutlined />,
    label: <Link to="/api-tester">API测试</Link>,
  },
  {
    key: '/request-collections',
    icon: <GroupOutlined />,
    label: <Link to="/request-collections">请求集合</Link>,
    children: [
      {
        key: '/request-collections',
        label: <Link to="/request-collections">集合列表</Link>,
      },
      {
        key: '/request-collections/yaml-upload',
        label: <Link to="/request-collections/yaml-upload">YAML上传</Link>,
      },
    ],
  },
  {
    key: '/feature-tests',
    icon: <FileTextOutlined />,
    label: <Link to="/feature-tests">功能测试</Link>,
  },
  {
    key: '/test-scripts',
    icon: <CodeOutlined />,
    label: <Link to="/test-scripts">测试脚本</Link>,
  },
  {
    key: '/ui-tests',
    icon: <PlayCircleOutlined />,
    label: <Link to="/ui-tests">UI测试</Link>,
  },
  {
    key: '/ai-test-analysis',
    icon: <RobotOutlined />,
    label: <Link to="/ai-test-analysis">AI分析用例</Link>,
  },
];

function App() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Find the current selected key, handling nested routes
  const getSelectedKey = () => {
    const currentPath = location.pathname;
    // Find the key that is the best match for the start of the path
    const bestMatch = menuItems.map(item => item.key).sort((a, b) => b.length - a.length).find(key => currentPath.startsWith(key));
    return bestMatch || '/';
  };

  // 用户菜单
  const userMenu = [
    {
      key: 'profile',
      label: '个人信息',
      icon: <UserOutlined />,
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      danger: true,
    },
  ];

  const handleMenuClick = (e) => {
    if (e.key === 'logout') {
      logout();
      message.success('已退出登录');
      navigate('/login', { replace: true });
    }
  };

  const menu = (
    <Menu onClick={handleMenuClick} items={userMenu} />
  );

  // 如果未登录，不显示侧边栏和菜单，只显示Outlet
  if (!user) {
    return <Outlet />;
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: '32px', margin: '16px', background: 'rgba(255, 255, 255, 0.2)', borderRadius: '6px', color: 'white', textAlign: 'center', lineHeight: '32px' }}>
          JTest
        </div>
        <Menu theme="dark" selectedKeys={[getSelectedKey()]} mode="inline" items={menuItems} />
      </Sider>
      <Layout className="site-layout">
        <Header style={{ padding: '0 24px', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} >
          <h2 style={{ margin: 0 }}>测试平台</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <MemberManager />
            {user && (
              <Dropdown overlay={menu} placement="bottomRight" arrow>
                <Space style={{ cursor: 'pointer' }}>
                  <Avatar icon={<UserOutlined />} />
                  <span>{user.username}</span>
                </Space>
              </Dropdown>
            )}
          </div>
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
