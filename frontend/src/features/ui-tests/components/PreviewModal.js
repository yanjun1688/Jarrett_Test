/**
 * 预览脚本弹窗组件
 */
import React, { useMemo } from 'react';
import { Modal, Button, Space, Descriptions, Tag, Typography, Divider, Radio, Alert, Timeline, Card } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { ACTION_LABELS, ACTION_ICONS, ACTION_COLORS, getColorHex, DEFAULT_CONFIG } from '../../../constants';
import '../../../css/UiTestManager.css';

const { Title, Text } = Typography;

const PreviewModal = ({ visible, previewResult, previewMode, onClose, onModeChange }) => {
  // 获取actions并按order排序
  const sortedActions = useMemo(() => {
    if (!previewResult?.actions) return [];
    return [...previewResult.actions].sort((a, b) => {
      const orderA = a.order || 0;
      const orderB = b.order || 0;
      return orderA - orderB;
    });
  }, [previewResult?.actions]);

  return (
    <Modal
      title="预览脚本"
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={1200}
    >
      {previewResult && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 脚本基本信息 */}
          <Descriptions bordered column={2}>
            <Descriptions.Item label="脚本名称">
              {previewResult.name}
            </Descriptions.Item>
            <Descriptions.Item label="浏览器">
              {previewResult.browser_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="无头模式">
              <Tag color={previewResult.headless ? 'blue' : 'green'}>
                {previewResult.headless ? '无头' : '可见'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="视口尺寸">
              {previewResult.viewport_width || DEFAULT_CONFIG.VIEWPORT_WIDTH} x {previewResult.viewport_height || DEFAULT_CONFIG.VIEWPORT_HEIGHT}
            </Descriptions.Item>
            {previewResult.description && (
              <Descriptions.Item label="描述" span={2}>
                {previewResult.description}
              </Descriptions.Item>
            )}
          </Descriptions>

          <Divider />

          {/* 模式切换 */}
          <div className="ui-test-preview-mode-switcher">
            <Radio.Group
              value={previewMode}
              onChange={(e) => onModeChange(e.target.value)}
              buttonStyle="solid"
            >
              <Radio.Button value="list">列表模式</Radio.Button>
              <Radio.Button value="visual">可视化预览</Radio.Button>
            </Radio.Group>
          </div>

          {/* Actions数据 */}
          {sortedActions.length === 0 ? (
            <Alert
              message="脚本内容为空"
              description="该脚本没有配置任何actions。请先编辑脚本添加actions。"
              type="warning"
            />
          ) : previewMode === 'list' ? (
            // 列表模式
            <div>
              <Title level={5}>测试Actions（共 {sortedActions.length} 个）</Title>
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {sortedActions.map((action, index) => {
                  const ActionIcon = ACTION_ICONS[action.type] || ThunderboltOutlined;
                  const actionColor = ACTION_COLORS[action.type] || 'default';
                  
                  return (
                    <Card 
                      key={action.id || index} 
                      size="small" 
                      className="ui-test-preview-action-card"
                      style={{ borderLeft: `4px solid ${getColorHex(actionColor)}` }}
                    >
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <div className="ui-test-preview-action-header">
                          <ActionIcon className="ui-test-preview-action-icon" style={{ color: getColorHex(actionColor) }} />
                          <Tag color={actionColor}>
                            {ACTION_LABELS[action.type] || action.type}
                          </Tag>
                          <Text type="secondary">步骤 {action.order || index + 1}</Text>
                          {action.id && (
                            <Text type="secondary" className="ui-test-preview-action-id">
                              (ID: {action.id})
                            </Text>
                          )}
                        </div>
                        
                        {action.description && (
                          <div>
                            <Text strong>说明：</Text>
                            <Text>{action.description}</Text>
                          </div>
                        )}
                        
                        {action.selector && (
                          <div>
                            <Text strong>元素定位：</Text>
                            <Tag color="blue">
                              {typeof action.selector === 'object' 
                                ? `${action.selector.type || action.selector.locator_type || 'css'} = ${action.selector.value || action.selector.locator_value || ''}`
                                : action.selector}
                            </Tag>
                          </div>
                        )}
                        
                        {action.params && Object.keys(action.params).length > 0 && (
                          <div>
                            <Text strong>参数：</Text>
                            <pre className="ui-test-preview-json-pre">
                              {JSON.stringify(action.params, null, 2)}
                            </pre>
                          </div>
                        )}
                      </Space>
                    </Card>
                  );
                })}
              </Space>
            </div>
          ) : (
            // 可视化预览模式
            <div>
              <Title level={5}>执行流程预览（共 {sortedActions.length} 步）</Title>
              <Timeline className="ui-test-preview-timeline">
                {sortedActions.map((action, index) => {
                  const ActionIcon = ACTION_ICONS[action.type] || ThunderboltOutlined;
                  const actionColor = ACTION_COLORS[action.type] || 'default';
                  
                  // 构建详细描述
                  const details = [];
                  if (action.description) {
                    details.push(`说明: ${action.description}`);
                  }
                  if (action.selector) {
                    const selectorText = typeof action.selector === 'object' 
                      ? `${action.selector.type || action.selector.locator_type || 'css'} = ${action.selector.value || action.selector.locator_value || ''}`
                      : action.selector;
                    details.push(`定位: ${selectorText}`);
                  }
                  if (action.params && Object.keys(action.params).length > 0) {
                    const paramsText = Object.entries(action.params)
                      .map(([key, value]) => `${key}: ${value}`)
                      .join(', ');
                    details.push(`参数: ${paramsText}`);
                  }
                  
                  return (
                    <Timeline.Item
                      key={action.id || index}
                      dot={<ActionIcon style={{ fontSize: '16px', color: getColorHex(actionColor) }} />}
                      color={actionColor}
                    >
                      <Card size="small" className="ui-test-preview-timeline-card">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div className="ui-test-preview-action-header">
                            <Tag color={actionColor}>
                              {ACTION_LABELS[action.type] || action.type}
                            </Tag>
                            <Text type="secondary">步骤 {action.order || index + 1}</Text>
                          </div>
                          {details.length > 0 && (
                            <Space direction="vertical" size={4}>
                              {details.map((detail, idx) => (
                                <Text key={idx} type="secondary" className="ui-test-preview-timeline-text">
                                  {detail}
                                </Text>
                              ))}
                            </Space>
                          )}
                        </Space>
                      </Card>
                    </Timeline.Item>
                  );
                })}
              </Timeline>
            </div>
          )}
        </Space>
      )}
    </Modal>
  );
};

export default React.memo(PreviewModal);
