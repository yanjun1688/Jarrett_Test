/**
 * ChatBot 设置面板组件
 */
import React from 'react';
import { Divider, Select, Input } from 'antd';
import '../../styles/chatbot-settings.css';

const { TextArea } = Input;
const { Option } = Select;

const ChatBotSettings = ({
  visible = false,
  models = [],
  selectedModel,
  systemMessage,
  onModelChange,
  onSystemMessageChange,
}) => {
  if (!visible) return null;

  return (
    <div className="chatbot-settings">
      <Divider style={{ margin: '12px 0' }}>设置</Divider>
      <div className="setting-item">
        <label>AI 模型</label>
        <Select
          value={selectedModel?.name || undefined}
          onChange={(value) => {
            const model = models.find(m => m.name === value);
            onModelChange(model);
          }}
          style={{ width: '100%' }}
          placeholder="选择模型"
          loading={models.length === 0}
        >
          {models.map(model => (
            <Option key={model.id || model.name} value={model.name}>
              {model.name} - {model.display_name || model.id}
            </Option>
          ))}
        </Select>
      </div>
      <div className="setting-item">
        <label>系统提示词</label>
        <TextArea
          value={systemMessage}
          onChange={(e) => onSystemMessageChange(e.target.value)}
          rows={3}
          placeholder="设置 AI 的角色和行为"
        />
      </div>
    </div>
  );
};

export default React.memo(ChatBotSettings);