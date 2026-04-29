import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Button, Space } from 'antd';
import OptionList from './ChatBot/OptionList';
import ConfirmDialog from './ChatBot/ConfirmDialog';
import './ChatBotMessageRenderer.css';

const parseMCPTextContent = (text) => {
  if (!text || typeof text !== 'string') return text;
  
  if (!text.includes('TextContent(')) return text;
  
  const textMatches = [];
  const regex = /TextContent\([^)]*text=['"]([^'"]+)['"]/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    textMatches.push(match[1]);
  }
  
  if (textMatches.length > 0) {
    return textMatches.join('\n\n');
  }
  
  const jsonMatch = text.match(/\[?\s*\{[^{}]*"type"\s*:\s*"text"[^{}]*"text"\s*:\s*"([^"]+)"[^{}]*\}\s*\]?/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0].replace(/'/g, '"'));
      if (Array.isArray(parsed)) {
        return parsed.map(item => item.text || '').join('\n\n');
      }
      return parsed.text || text;
    } catch (e) {
      return text;
    }
  }
  
  return text;
};

const parseToolResultData = (toolResult) => {
  if (!toolResult) return null;
  
  try {
    if (typeof toolResult === 'string') {
      const parsed = JSON.parse(toolResult);
      return parsed?.data || null;
    }
    return toolResult?.data || null;
  } catch {
    return null;
  }
};

const ChatBotMessageRenderer = ({ content, onOptionSelect, onSendMessage }) => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingData, setPendingData] = useState(null);
  
  if (!content) return null;
  
  let markdownText = '';
  let toolResultData = null;
  
  if (typeof content === 'string') {
    markdownText = parseMCPTextContent(content);
  } else if (content.type === 'progress') {
    const { logs, processing, result } = content;
    
    let progressMd = processing ? '### AI 正在处理\n\n' : '### 处理完成\n\n';
    
    if (logs && logs.length > 0) {
      logs.forEach(log => {
        if (log.type === 'info') progressMd += `> ${log.message}\n\n`;
        else if (log.type === 'intent') progressMd += `> 意图: ${log.intent || '未知'}${log.confidence ? ` (${(log.confidence * 100).toFixed(0)}%)` : ''}\n\n`;
        else if (log.type === 'tool') progressMd += `> 工具: ${log.tool || '未知'}${log.step ? ` - ${log.step}` : ''}\n\n`;
        else if (log.type === 'success') progressMd += `> ${log.message}\n\n`;
        else if (log.type === 'error') progressMd += `> ${log.message}\n\n`;
        else if (log.message) progressMd += `> ${log.message}\n\n`;
      });
    }
    
    if (result) {
      if (result.message || result.response) {
        progressMd += '---\n\n' + parseMCPTextContent(result.message || result.response);
      }
      if (result.tool_result) {
        toolResultData = parseToolResultData(result.tool_result);
        if (!toolResultData) {
          const resultText = typeof result.tool_result === 'string' 
            ? parseMCPTextContent(result.tool_result) 
            : JSON.stringify(result.tool_result, null, 2);
          progressMd += '---\n\n' + resultText;
        }
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
    
    let md = parseMCPTextContent(message || response || '');
    
    if (tool_result) {
      toolResultData = parseToolResultData(tool_result);
      if (!toolResultData) {
        const toolResultText = typeof tool_result === 'string' 
          ? parseMCPTextContent(tool_result) 
          : JSON.stringify(tool_result, null, 2);
        if (toolResultText) {
          md += '\n\n---\n\n' + toolResultText;
        }
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
  
  if (!markdownText && !toolResultData) return null;
  
  return (
    <div className="markdown-content">
      {markdownText && (
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
          {markdownText}
        </ReactMarkdown>
      )}
      
      {toolResultData?.options && (
        <OptionList
          options={toolResultData.options}
          title={toolResultData.message || '请选择：'}
          onSelect={(item) => {
            if (onOptionSelect) {
              onOptionSelect(item);
            } else if (onSendMessage) {
              onSendMessage(`选择: ${item.label} (ID: ${item.id})`);
            }
          }}
        />
      )}
      
      {toolResultData?.preview && !toolResultData?.options && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 500, marginBottom: 8 }}>
            {toolResultData.message || '已生成测试用例，请确认：'}
          </div>
          <div style={{ 
            background: '#f5f5f5', 
            padding: 12, 
            borderRadius: 4,
            maxHeight: 200,
            overflow: 'auto'
          }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {toolResultData.preview}
            </ReactMarkdown>
          </div>
          <Space style={{ marginTop: 12 }}>
            <Button 
              type="primary"
              onClick={() => {
                setPendingData(toolResultData);
                setConfirmOpen(true);
              }}
            >
              确认保存
            </Button>
            <Button onClick={() => {
              if (onSendMessage) {
                onSendMessage('取消保存，重新生成');
              }
            }}>
              取消
            </Button>
            <Button 
              type="link"
              onClick={() => {
                setPendingData(toolResultData);
                setConfirmOpen(true);
              }}
            >
              查看完整内容
            </Button>
          </Space>
          
          <ConfirmDialog
            open={confirmOpen}
            preview={pendingData?.full_content || pendingData?.preview || ''}
            message="请确认是否保存以下测试用例："
            onConfirm={() => {
              setConfirmOpen(false);
              if (onSendMessage) {
                onSendMessage(`确认保存，project_id: ${pendingData?.project_id || ''}, document_id: ${pendingData?.document_id || ''}`);
              }
            }}
            onCancel={() => setConfirmOpen(false)}
          />
        </div>
      )}
      
      {toolResultData?.saved_count && (
        <div style={{ marginTop: 8, color: '#52c41a' }}>
          {toolResultData.message || `成功保存 ${toolResultData.saved_count} 条测试用例`}
        </div>
      )}
      
      {toolResultData?.script_id && (
        <div style={{ marginTop: 8, color: '#52c41a' }}>
          {toolResultData.message || `成功保存脚本：${toolResultData.script_name}`}
        </div>
      )}
    </div>
  );
};

export default ChatBotMessageRenderer;