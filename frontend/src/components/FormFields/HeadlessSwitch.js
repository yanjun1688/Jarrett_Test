/**
 * 无头模式开关 - 可复用的表单字段组件
 */
import React from 'react';
import { Form, Switch } from 'antd';
import { DEFAULT_CONFIG } from '../../constants';

const HeadlessSwitch = ({ 
  name = 'headless',
  label = '无头模式',
  defaultValue = DEFAULT_CONFIG.HEADLESS,
  ...formItemProps 
}) => {
  return (
    <Form.Item
      label={label}
      name={name}
      valuePropName="checked"
      initialValue={defaultValue}
      {...formItemProps}
    >
      <Switch checkedChildren="无头" unCheckedChildren="可见" />
    </Form.Item>
  );
};

export default HeadlessSwitch;
