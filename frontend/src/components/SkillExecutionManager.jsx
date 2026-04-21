import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Button,
  Input,
  List,
  Card,
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
  CheckCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { skillExecutionAPI } from '../api/skillExecution';

const { Text, Paragraph } = Typography;

/**
 * Skill 管理组件
 * 提供搜索远程 Skill 和安装到本地功能
 */
const SkillExecutionManager = ({ visible, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  
  const [searchKeyword, setSearchKeyword] = useState('');
  const [remoteSkills, setRemoteSkills] = useState([]);
  const [localSkills, setLocalSkills] = useState([]);
  
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
      setRemoteSkills([]);
      setSearchKeyword('');
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
        setRemoteSkills(response.data.data?.skills || []);
        if (response.data.data?.skills?.length === 0) {
          message.info('未找到匹配的 Skill');
        }
      } else {
        message.error(response.data?.error || '搜索失败');
      }
    } catch (error) {
      message.error('搜索失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (skillName) => {
    setInstalling(true);
    try {
      const response = await skillExecutionAPI.installSkill(skillName);
      if (response.data?.success) {
        message.success(response.data.data?.message || '安装成功');
        loadLocalSkills();
      } else {
        message.error(response.data?.error || '安装失败');
      }
    } catch (error) {
      message.error('安装失败: ' + (error.response?.data?.error || error.message));
    } finally {
      setInstalling(false);
    }
  };

  const isSkillInstalled = (skillName) => {
    const basename = skillName.split('/')[-1].split('@')[0];
    return localSkills.some(s => s.name === basename);
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

      {remoteSkills.length > 0 && (
        <List
          grid={{ gutter: 16, column: 2 }}
          dataSource={remoteSkills}
          renderItem={(skill) => {
            const skillFullName = skill.id || skill.name;
            const installed = isSkillInstalled(skillFullName);
            const basename = skillFullName.split('/')[-1].split('@')[0];
            
            return (
              <List.Item>
                <Card
                  title={
                    <Space>
                      <ToolOutlined />
                      <Text strong>{basename}</Text>
                      {skill.version && <Tag size="small">v{skill.version}</Tag>}
                      {installed && <Tag color="success">已安装</Tag>}
                    </Space>
                  }
                  extra={
                    installed ? (
                      <Tag icon={<CheckCircleOutlined />} color="success">
                        已安装
                      </Tag>
                    ) : (
                      <Button 
                        type="primary" 
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => handleInstall(skillFullName)}
                        loading={installing}
                      >
                        安装
                      </Button>
                    )
                  }
                >
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                    {skill.description || '暂无描述'}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {skillFullName}
                  </Text>
                </Card>
              </List.Item>
            );
          }}
        />
      )}

      {remoteSkills.length === 0 && !loading && searchKeyword && (
        <Empty description="未找到匹配的 Skill" />
      )}

      {remoteSkills.length === 0 && !loading && !searchKeyword && (
        <Alert
          type="info"
          message="搜索远程 Skill"
          description="输入关键词搜索 skill.sh 社区的技能，找到后点击安装即可在 ChatBot 中使用"
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
        <List
          grid={{ gutter: 16, column: 2 }}
          dataSource={localSkills}
          renderItem={(skill) => (
            <List.Item>
              <Card
                title={
                  <Space>
                    <ToolOutlined />
                    <Text strong>{skill.name}</Text>
                    <Tag color={skill.source === 'builtin' ? 'blue' : 'green'}>
                      {skill.source === 'builtin' ? '内置' : '已安装'}
                    </Tag>
                  </Space>
                }
              >
                <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                  {skill.description || '暂无描述'}
                </Paragraph>
                {skill.version && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    版本: {skill.version}
                  </Text>
                )}
              </Card>
            </List.Item>
          )}
        />
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