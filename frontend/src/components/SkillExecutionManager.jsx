import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Button,
  Input,
  Space,
  Typography,
  Alert,
  message,
  Tag,
  Empty,
  Divider,
  Spin
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  ToolOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import Ansi from 'ansi-to-react';
import { skillExecutionAPI } from '../api/skillExecution';

const { Text } = Typography;

/**
 * Skill 管理组件
 * 提供搜索远程 Skill 和安装到本地功能
 */
const SkillExecutionManager = ({ visible, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchOutput, setSearchOutput] = useState('');
  const [localSkills, setLocalSkills] = useState([]);
  const [installInput, setInstallInput] = useState('');
  
  const [activeTab, setActiveTab] = useState('search');

  const loadLocalSkills = useCallback(async () => {
    setLoading(true);
    try {
      const response = await skillExecutionAPI.getLocalSkills();
      if (response.data?.success) {
        setLocalSkills(response.data.data?.skills || []);
      }
    } catch (error) {
      message.error('加载本地技能失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (visible) {
      loadLocalSkills();
      setSearchOutput('');
      setSearchKeyword('');
      setInstallInput('');
      setActiveTab('search');
    }
  }, [visible, loadLocalSkills]);

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }
    
    setLoading(true);
    try {
      const response = await skillExecutionAPI.searchSkills(searchKeyword);
      if (response.data?.success) {
        // MCP Server 返回格式: {success, output, error}
        setSearchOutput(response.data.output || '');
        if (!response.data.output) {
          message.info('未找到匹配的 Skill');
        }
      } else {
        message.error(response.data?.error || '搜索失败');
        setSearchOutput('');
      }
    } catch (error) {
      message.error('搜索失败: ' + (error.response?.data?.error || error.message));
      setSearchOutput('');
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async () => {
    if (!installInput.trim()) {
      message.warning('请输入要安装的 Skill ID');
      return;
    }
    
    setInstalling(true);
    try {
      const response = await skillExecutionAPI.installSkill(installInput.trim());
      if (response.data?.success) {
        message.success(response.data.message || '安装成功');
        loadLocalSkills();
        setInstallInput('');
      } else {
        message.error(response.data?.error || '安装失败');
      }
    } catch (error) {
      message.error('安装失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setInstalling(false);
    }
  };

  const renderSearchPanel = () => (
    <div>
      <Input.Search
        placeholder="搜索 Skill（如：api、test、webapp）"
        value={searchKeyword}
        onChange={(e) => setSearchKeyword(e.target.value)}
        onSearch={handleSearch}
        enterButton={<><SearchOutlined /> 搜索</>}
        size="large"
        loading={loading}
        style={{ marginBottom: 16 }}
      />

      {searchOutput && (
        <>
          <div style={{ 
            background: '#1e1e1e', 
            padding: '16px', 
            borderRadius: '8px',
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            overflow: 'auto',
            maxHeight: '400px',
            marginBottom: '16px'
          }}>
            <Ansi>{searchOutput}</Ansi>
          </div>
          
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ marginRight: 8 }}>
              输入要安装的 Skill ID：
            </Text>
            <Input
              placeholder="如: owner/repo@skill"
              value={installInput}
              onChange={(e) => setInstallInput(e.target.value)}
              style={{ width: 300, marginRight: 8 }}
            />
            <Button 
              type="primary" 
              icon={<DownloadOutlined />}
              onClick={handleInstall}
              loading={installing}
            >
              安装
            </Button>
          </div>
        </>
      )}

      {!searchOutput && !loading && searchKeyword && (
        <Empty description="未找到匹配的 Skill" />
      )}

      {!searchOutput && !loading && !searchKeyword && (
        <Alert
          type="info"
          message="搜索远程 Skill"
          description="输入关键词搜索 skill.sh 社区的技能，在终端输出中找到想要的 Skill ID，然后输入安装"
          showIcon
        />
      )}
    </div>
  );

  const renderLocalPanel = () => (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={loadLocalSkills} loading={loading}>
          刷新
        </Button>
      </Space>

      {localSkills.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          {localSkills.map((skill) => (
            <div key={skill.name} style={{
              border: '1px solid #d9d9d9',
              borderRadius: 8,
              padding: 16
            }}>
              <Space style={{ marginBottom: 8 }}>
                <ToolOutlined />
                <Text strong>{skill.name}</Text>
                <Tag color={skill.source === 'builtin' ? 'blue' : 'green'}>
                  {skill.source === 'builtin' ? '内置' : '已安装'}
                </Tag>
              </Space>
              <div style={{ color: '#666', fontSize: 14 }}>
                {skill.description || '暂无描述'}
              </div>
              {skill.version && (
                <div style={{ color: '#999', fontSize: 12, marginTop: 8 }}>
                  版本: {skill.version}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {localSkills.length === 0 && !loading && (
        <Empty description="暂无已安装的 Skill" />
      )}
    </div>
  );

  return (
    <Modal
      title={
        <Space>
          <ToolOutlined />
          <span>Skill 管理</span>
        </Space>
      }
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={null}
    >
      <Space style={{ marginBottom: 16 }}>
        <Button 
          type={activeTab === 'search' ? 'primary' : 'default'}
          onClick={() => setActiveTab('search')}
        >
          搜索安装
        </Button>
        <Button 
          type={activeTab === 'local' ? 'primary' : 'default'}
          onClick={() => setActiveTab('local')}
        >
          本地技能 ({localSkills.length})
        </Button>
      </Space>

      <Divider />

      <Spin spinning={loading}>
        {activeTab === 'search' && renderSearchPanel()}
        {activeTab === 'local' && renderLocalPanel()}
      </Spin>
    </Modal>
  );
};

export default SkillExecutionManager;