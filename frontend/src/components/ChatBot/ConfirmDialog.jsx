/**
 * ChatBot 确认弹窗组件
 * 用于确认生成的测试用例/脚本是否保存
 */
import React from 'react';
import { Modal, Button, Typography, Space } from 'antd';

const { Text } = Typography;

const ConfirmDialog = ({
  open,
  preview,
  message,
  onConfirm,
  onCancel,
  loading = false
}) => {
  if (!preview) return null;

  return (
    <Modal
      open={open}
      title="确认保存"
      footer={null}
      width={600}
      onCancel={onCancel}
      maskClosable={false}
    >
      <div style={{ marginBottom: 16 }}>
        <Text strong>{message || '请确认是否保存以下内容：'}</Text>
      </div>
      
      <div 
        style={{ 
          background: '#f5f5f5', 
          padding: 12, 
          borderRadius: 4,
          maxHeight: 300,
          overflow: 'auto',
          marginBottom: 16,
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          fontSize: 12
        }}
      >
        {preview}
      </div>
      
      <Space>
        <Button type="primary" onClick={onConfirm} loading={loading}>
          确认保存
        </Button>
        <Button onClick={onCancel} disabled={loading}>
          取消
        </Button>
      </Space>
    </Modal>
  );
};

export default React.memo(ConfirmDialog);