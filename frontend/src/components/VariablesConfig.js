import React from 'react';
import { Table, Button, Input, Tooltip, Space, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';

const VariablesConfig = ({ value = [], onChange }) => {
  const handleAdd = () => {
    const newVariable = { key: '', value: '' };
    onChange([...value, newVariable]);
  };

  const handleRemove = (index) => {
    const newVariables = value.filter((_, i) => i !== index);
    onChange(newVariables);
  };

  const handleChange = (index, field, newValue) => {
    const newVariables = [...value];
    newVariables[index] = { ...newVariables[index], [field]: newValue };
    onChange(newVariables);
  };

  // 验证变量名格式
  const validateVariableName = (name) => {
    return /^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(name);
  };

  const columns = [
    {
      title: (
        <Space>
          变量名
          <Tooltip title="变量名只能包含字母、数字、下划线和连字符，且必须以字母或下划线开头">
            <InfoCircleOutlined style={{ color: '#1890ff' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'key',
      width: '40%',
      render: (text, record, index) => {
        const isValid = text ? validateVariableName(text) : true;
        return (
          <Input
            value={text}
            placeholder="例如: baseUrl 或 api_token"
            onChange={(e) => handleChange(index, 'key', e.target.value)}
            status={!isValid ? 'error' : ''}
          />
        );
      },
    },
    {
      title: '变量值',
      dataIndex: 'value',
      width: '45%',
      render: (text, record, index) => (
        <Input
          value={text}
          placeholder="例如: https://api.example.com"
          onChange={(e) => handleChange(index, 'value', e.target.value)}
        />
      ),
    },
    {
      title: '预览',
      width: '15%',
      render: (_, record, index) => {
        const variableName = record.key || '未命名';
        const isValid = record.key ? validateVariableName(record.key) : true;
        
        return (
          <div>
            {!record.key ? (
              <Tag color="default">未设置</Tag>
            ) : isValid ? (
              <Tooltip title={`此变量将在请求中使用 {{${variableName}}} 格式引用`}>
                <Tag color="processing">{{variableName}}</Tag>
              </Tooltip>
            ) : (
              <Tag color="error">格式错误</Tag>
            )}
          </div>
        );
      },
    },
    {
      title: '操作',
      width: '10%',
      render: (_, record, index) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => handleRemove(index)}
        />
      ),
    },
  ];

  // 添加使用说明
  const variablesInstruction = (
    <div style={{ marginBottom: 16 }}>
      <Space>
        <strong>使用说明:</strong>
        <Tag color="blue">设置变量</Tag>
        <span>在创建的变量将在后面 API 请求的 URL、Headers、Body 中使用</span>
        <Tag color="processing">{'{{变量名}}'}</Tag>
        <span>的方式引用</span>
      </Space>
    </div>
  );

  return (
    <div>
      {variablesInstruction}
      <Table
        columns={columns}
        dataSource={value}
        pagination={false}
        size="small"
        rowKey={(record, index) => index}
        locale={{ emptyText: '暂无变量，点击下方按钮添加' }}
        expandable={{
          expandedRowRender: (record) => {
            const variableName = record.key || '未命名';
            return (
              <p style={{ margin: 0, color: '#666' }}>
                <strong>示例:</strong> 在请求中使用 <code>{`{{${variableName}}}`}</code> 来引用这个变量的值
              </p>
            );
          },
          rowExpandable: (record) => record.key && record.value,
        }}
      />
      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={handleAdd}
        style={{ marginTop: 8, width: '100%' }}
      >
        添加变量
      </Button>
    </div>
  );
};

export default VariablesConfig;