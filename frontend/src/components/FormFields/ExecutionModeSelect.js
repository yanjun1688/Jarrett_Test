/**
 * 执行模式选择器 - 可复用的表单字段组件
 */
import React from 'react';
import { Form, Select } from 'antd';
import { EXECUTION_MODES } from '../../constants';

const ExecutionModeSelect = ({ 
  name = 'execution_mode',
  label = '执行模式',
  defaultValue = EXECUTION_MODES.CONCURRENT,
  required = true,
  onChange,
  ...formItemProps 
}) => {
  return (
    <Form.Item
      label={label}
      name={name}
      initialValue={defaultValue}
      rules={required ? [{ required: true, message: '请选择执行模式' }] : []}
      {...formItemProps}
    >
      <Select onChange={onChange}>
        <Select.Option value={EXECUTION_MODES.CONCURRENT} title="所有请求同时执行">
          并发执行
        </Select.Option>
        <Select.Option value={EXECUTION_MODES.SEQUENTIAL} title="请求按顺序逐个执行">
          顺序执行
        </Select.Option>
        <Select.Option value={EXECUTION_MODES.CHAIN} title="请求按顺序执行，支持变量提取和传递">
          链式执行（支持变量传递）
        </Select.Option>
      </Select>
    </Form.Item>
  );
};

export default ExecutionModeSelect;
