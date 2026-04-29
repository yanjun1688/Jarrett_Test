/**
 * 工具结果渲染组件
 * 根据 tool_result.data 内容自动判断渲染类型：
 * - options 存在 → 渲染选项列表
 * - preview 存在 → 渲染预览 + 确认/取消按钮
 * - saved_count 存在 → 渲染保存成功消息
 * - 其他 → 正常消息显示
 */
import React from 'react';
import { Button, Space, Typography, message } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import OptionList from './OptionList';

const { Text } = Typography;

const ToolResultRenderer = ({
  data,
  onSendMessage
}) => {
  if (!data) return null;

  // 渲染选项列表
  if (data.options && Array.isArray(data.options)) {
    return (
      <OptionList
        options={data.options}
        title={data.message || '请选择：'}
        onSelect={(item) => {
          if (onSendMessage) {
            // 发送选项ID作为消息，AI会根据上下文处理
            onSendMessage(`用户选择了: ${item.id}`);
          }
        }}
      />
    );
  }

  // 渲染预览 + 确认按钮
  if (data.preview) {
    const handleConfirmSave = () => {
      if (onSendMessage && data.full_content) {
        // 发送保存请求，包含完整内容
        const saveMessage = `请保存以下测试用例到项目:\n\n${data.full_content}`;
        onSendMessage(saveMessage);
        message.info('正在保存...');
      } else if (onSendMessage) {
        onSendMessage('确认保存');
      }
    };

    const handleCancel = () => {
      if (onSendMessage) {
        onSendMessage('取消保存，请重新生成');
      }
    };

    return (
      <div style={{ marginBottom: 12 }}>
        <Text strong>{data.message || '已生成测试用例：'}</Text>
        <div 
          style={{ 
            background: '#f5f5f5', 
            padding: 12, 
            borderRadius: 4,
            maxHeight: 200,
            overflow: 'auto',
            marginBottom: 12,
            marginTop: 8
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {data.preview}
          </ReactMarkdown>
        </div>
        {data.quality_score && (
          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
            质量评分: {data.quality_score}/100
          </Text>
        )}
        <Space>
          <Button 
            type="primary" 
            onClick={handleConfirmSave}
          >
            确认保存
          </Button>
          <Button onClick={handleCancel}>
            取消重新生成
          </Button>
        </Space>
      </div>
    );
  }

  // 渲染保存成功消息
  if (data.saved_count) {
    return (
      <div>
        <Text type="success">{data.message || `成功保存 ${data.saved_count} 条测试用例`}</Text>
        {data.view_url && (
          <Button 
            type="link" 
            size="small"
            onClick={() => window.open(data.view_url, '_blank')}
          >
            查看用例
          </Button>
        )}
      </div>
    );
  }

  // 渲染脚本保存成功消息
  if (data.script_id) {
    return (
      <div>
        <Text type="success">{data.message || '成功保存脚本'}</Text>
        {data.view_url && (
          <Button 
            type="link" 
            size="small"
            onClick={() => window.open(data.view_url, '_blank')}
          >
            查看脚本
          </Button>
        )}
      </div>
    );
  }

  // 默认：渲染消息文本
  return (
    <Text>{data.message || JSON.stringify(data)}</Text>
  );
};

export default React.memo(ToolResultRenderer);