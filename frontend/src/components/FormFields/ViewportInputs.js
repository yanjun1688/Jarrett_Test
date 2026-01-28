/**
 * 视口配置输入 - 可复用的表单字段组件
 */
import React from 'react';
import { Form, Input, Space } from 'antd';
import { DEFAULT_CONFIG } from '../../constants';

const ViewportInputs = ({ 
  widthName = 'viewport_width',
  heightName = 'viewport_height',
  timeoutName = 'timeout',
  showTimeout = true,
  ...formItemProps 
}) => {
  return (
    <Space size="large" style={{ display: 'flex' }}>
      <Form.Item
        label="视口宽度"
        name={widthName}
        initialValue={DEFAULT_CONFIG.VIEWPORT_WIDTH}
        style={{ width: 150 }}
        {...formItemProps}
      >
        <Input type="number" min={0} placeholder={DEFAULT_CONFIG.VIEWPORT_WIDTH.toString()} />
      </Form.Item>

      <Form.Item
        label="视口高度"
        name={heightName}
        initialValue={DEFAULT_CONFIG.VIEWPORT_HEIGHT}
        style={{ width: 150 }}
        {...formItemProps}
      >
        <Input type="number" min={0} placeholder={DEFAULT_CONFIG.VIEWPORT_HEIGHT.toString()} />
      </Form.Item>

      {showTimeout && (
        <Form.Item
          label="超时时间(ms)"
          name={timeoutName}
          initialValue={DEFAULT_CONFIG.TIMEOUT}
          style={{ width: 150 }}
          {...formItemProps}
        >
          <Input type="number" min={0} placeholder={DEFAULT_CONFIG.TIMEOUT.toString()} />
        </Form.Item>
      )}
    </Space>
  );
};

export default ViewportInputs;
