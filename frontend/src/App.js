import React from 'react';
import { Layout, Menu, Dropdown, Avatar, Space, message } from 'antd';
import {
  HomeOutlined,
  ProjectOutlined,
  FileTextOutlined,
  BarChartOutlined,
  CodeOutlined,
  ApiOutlined,
  UserOutlined,
  LogoutOutlined,
  RobotOutlined,
  PlayCircleOutlined,
  BranchesOutlined,
  AppstoreOutlined,
  BookOutlined,
} from '@ant-design/icons';
import MemberManager from './components/MemberManager';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { useNavigate } from 'react-router-dom';
import ChatBotFloatButton from './components/ChatBotFloatButton';
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
    icon: <AppstoreOutlined />,
    label: <Link to="/request-collections">请求集合</Link>,
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
  {
    key: '/test-flows',
    icon: <BranchesOutlined />,
    label: <Link to="/test-flows">测试流程</Link>,
  },
  {
    key: '/knowledge-base',
    icon: <BookOutlined />,
    label: <Link to="/knowledge-base">知识库</Link>,
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
      
      {/* ChatBot 智能助手 - 全局悬浮按钮 */}
      <ChatBotFloatButton
        title="JTest AI 助手"
        drawerWidth={500}
        defaultSystemMessage={`你是一个专业的测试工程师和 AI 助手，专精于帮助用户解决测试相关问题。

你的专业领域包括：
- UI 自动化测试（Playwright、Selenium）
- API 测试设计和执行
- 测试用例设计和管理
- 测试框架搭建和优化
- 测试最佳实践和模式
- 代码审查和优化建议

请用以下特点回答：
1. 清晰、专业、友好
2. 提供具体的代码示例
3. 解释原因和原理
4. 给出最佳实践建议
5. 在不确定时坦诚告知用户`}
      />
    </Layout>
  );
}

export default App;
