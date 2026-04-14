/**
 * SkillExecutionManager 使用示例
 * 
 * 这个文件展示了如何在 React 应用中使用 SkillExecutionManager 组件
 */

import React, { useState } from 'react';
import { Button, Space, message } from 'antd';
import { ToolOutlined } from '@ant-design/icons';
import SkillExecutionManager from '../components/SkillExecutionManager';

/**
 * 示例1: 在页面中直接使用
 */
const SkillExecutionExample = () => {
  const [visible, setVisible] = useState(false);

  return (
    <div style={{ padding: 24 }}>
      <h1>Skill 执行管理示例</h1>
      
      <Space>
        <Button 
          type="primary" 
          icon={<ToolOutlined />}
          onClick={() => setVisible(true)}
        >
          打开 Skill 管理器
        </Button>
      </Space>

      <SkillExecutionManager
        visible={visible}
        onCancel={() => setVisible(false)}
        onSuccess={(result) => {
          message.success('操作成功');
          console.log('执行结果:', result);
        }}
      />
    </div>
  );
};

/**
 * 示例2: 在 ChatBot 组件中集成
 * 可以在 ChatBot 界面添加一个按钮来打开 Skill 管理器
 */
const ChatBotWithSkillIntegration = () => {
  const [skillManagerVisible, setSkillManagerVisible] = useState(false);

  return (
    <div>
      {/* 假设这是 ChatBot 组件的内容 */}
      <div className="chatbot-header" style={{ padding: 16, borderBottom: '1px solid #e8e8e8' }}>
        <Space>
          <h3>AI 助手</h3>
          <Button 
            icon={<ToolOutlined />}
            onClick={() => setSkillManagerVisible(true)}
          >
            Skill 工具
          </Button>
        </Space>
      </div>

      {/* ChatBot 对话内容 */}
      <div className="chatbot-content" style={{ padding: 16, minHeight: 400 }}>
        {/* 对话消息列表 */}
      </div>

      {/* Skill 管理器弹窗 */}
      <SkillExecutionManager
        visible={skillManagerVisible}
        onCancel={() => setSkillManagerVisible(false)}
        onSuccess={(result) => {
          // 可以将执行结果发送到 ChatBot 对话中
          console.log('Skill 执行完成:', result);
          setSkillManagerVisible(false);
        }}
      />
    </div>
  );
};

/**
 * 示例3: 在菜单或侧边栏中添加 Skill 管理入口
 */
const SidebarWithSkillMenu = () => {
  const [skillManagerVisible, setSkillManagerVisible] = useState(false);

  const menuItems = [
    { key: 'dashboard', label: '首页', icon: '🏠' },
    { key: 'projects', label: '项目', icon: '📁' },
    { key: 'testcases', label: '测试用例', icon: '📝' },
    { key: 'skills', label: 'Skill 执行', icon: '🛠️', onClick: () => setSkillManagerVisible(true) },
    { key: 'settings', label: '设置', icon: '⚙️' },
  ];

  return (
    <div style={{ display: 'flex' }}>
      {/* 侧边栏菜单 */}
      <div style={{ width: 200, background: '#001529', minHeight: '100vh', color: '#fff' }}>
        <div style={{ padding: 16, fontSize: 18, fontWeight: 'bold' }}>
          JTest 测试平台
        </div>
        {menuItems.map(item => (
          <div
            key={item.key}
            style={{ 
              padding: '12px 24px', 
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
            onClick={item.onClick}
            onMouseEnter={(e) => e.currentTarget.style.background = '#1890ff'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <span style={{ marginRight: 8 }}>{item.icon}</span>
            {item.label}
          </div>
        ))}
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, padding: 24 }}>
        <h2>欢迎使用 JTest 测试平台</h2>
        <p>点击左侧 "Skill 执行" 菜单打开 Skill 管理器</p>
      </div>

      {/* Skill 管理器 */}
      <SkillExecutionManager
        visible={skillManagerVisible}
        onCancel={() => setSkillManagerVisible(false)}
        onSuccess={(result) => {
          message.success('Skill 执行成功');
          setSkillManagerVisible(false);
        }}
      />
    </div>
  );
};

export { SkillExecutionExample, ChatBotWithSkillIntegration, SidebarWithSkillMenu };
export default SkillExecutionExample;
