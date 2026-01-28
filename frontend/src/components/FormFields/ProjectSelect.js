/**
 * 项目选择器 - 可复用的表单字段组件
 */
import React from 'react';
import { Form, Select } from 'antd';

const { Option } = Select;

const ProjectSelect = ({ 
  projects = [], 
  allowClear = true, 
  placeholder = "可选：关联到某个项目",
  required = false,
  ...formItemProps 
}) => {
  return (
    <Form.Item
      label="所属项目"
      name="project"
      rules={required ? [{ required: true, message: '请选择项目' }] : []}
      {...formItemProps}
    >
      <Select allowClear={allowClear} placeholder={placeholder}>
        {projects.map((project) => (
          <Option key={project.id} value={project.id}>
            {project.name}
          </Option>
        ))}
      </Select>
    </Form.Item>
  );
};

export default ProjectSelect;
