import React from 'react';
import { Collapse, Tag, Divider, Typography, Space } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  ToolOutlined,
  BulbOutlined
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import ExecutionPieChart from './ExecutionPieChart';
import './ChatBotMessageRenderer.css';

const { Text } = Typography;

const ChatBotMessageRenderer = ({ content }) => {
  if (!content) return null;
  
  let markdownText = '';
  
  if (typeof content === 'string') {
    markdownText = content;
  } else if (content.type === 'progress') {
    const { logs, processing, result } = content;
    
    let progressMd = processing ? '### 🔄 AI 正在处理\n\n' : '### ✅ 处理完成\n\n';
    
    if (logs && logs.length > 0) {
      logs.forEach(log => {
        if (log.type === 'info') progressMd += `> ℹ️ ${log.message}\n\n`;
        else if (log.type === 'intent') progressMd += `> 💡 意图: ${log.intent || '未知'}${log.confidence ? ` (${(log.confidence * 100).toFixed(0)}%)` : ''}\n\n`;
        else if (log.type === 'tool') progressMd += `> 🔧 工具: ${log.tool || '未知'}${log.step ? ` - ${log.step}` : ''}\n\n`;
        else if (log.type === 'success') progressMd += `> ✅ ${log.message}\n\n`;
        else if (log.type === 'error') progressMd += `> ❌ ${log.message}\n\n`;
        else if (log.message) progressMd += `> ${log.message}\n\n`;
      });
    }
    
    if (result) {
      if (result.message || result.response) {
        progressMd += '---\n\n' + (result.message || result.response);
      } else if (result.tool_result) {
        const toolResult = result.tool_result;
        const resultText = typeof toolResult === 'string' 
          ? toolResult 
          : (toolResult?.data?.result || JSON.stringify(toolResult, null, 2));
        progressMd += '---\n\n' + resultText;
      }
    }
    
    markdownText = progressMd;
  } else {
    const {
      message,
      response,
      intent,
      intent_details,
      tool_used,
      tool_result,
      model
    } = content;
    
    let md = message || response || '';
    
    if (tool_result) {
      const toolResultText = typeof tool_result === 'string' 
        ? tool_result 
        : (tool_result?.data?.result || JSON.stringify(tool_result, null, 2));
      if (toolResultText) {
        md += '\n\n---\n\n' + toolResultText;
      }
    }
    
    if (intent) {
      md += `\n\n---\n\n**意图:** ${intent}`;
      if (intent_details?.confidence) {
        md += ` (${(intent_details.confidence * 100).toFixed(0)}%)`;
      }
      if (intent_details?.reasoning) {
        md += `\n\n**推理:** ${intent_details.reasoning}`;
      }
    }
    
    if (tool_used) {
      md += `\n\n**工具:** ${tool_result?.data?.skill_name || '已调用'}`;
    }
    
    if (model) {
      md += `\n\n**模型:** ${model}`;
    }
    
    markdownText = md;
  }
  
  if (!markdownText) return null;
  
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
        {markdownText}
      </ReactMarkdown>
    </div>
  );
};

export default ChatBotMessageRenderer;