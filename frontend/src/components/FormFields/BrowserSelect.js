/**
 * 浏览器选择器 - 可复用的表单字段组件
 */
import React from 'react';
import { Form, Select } from 'antd';
import { BROWSER_TYPES, BROWSER_TYPE_LABELS } from '../../constants';

const BrowserSelect = ({ 
  name = 'browser_type',
  label = '浏览器',
  defaultValue = BROWSER_TYPES.CHROMIUM,
  ...formItemProps 
}) => {
  return (
    <Form.Item
      label={label}
      name={name}
      initialValue={defaultValue}
      {...formItemProps}
    >
      <Select>
        <Select.Option value={BROWSER_TYPES.CHROMIUM}>
          {BROWSER_TYPE_LABELS[BROWSER_TYPES.CHROMIUM]}
        </Select.Option>
        <Select.Option value={BROWSER_TYPES.FIREFOX}>
          {BROWSER_TYPE_LABELS[BROWSER_TYPES.FIREFOX]}
        </Select.Option>
        <Select.Option value={BROWSER_TYPES.WEBKIT}>
          {BROWSER_TYPE_LABELS[BROWSER_TYPES.WEBKIT]}
        </Select.Option>
      </Select>
    </Form.Item>
  );
};

export default BrowserSelect;
