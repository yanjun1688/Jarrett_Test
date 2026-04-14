import React from 'react';
import { Table, Button, Input } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';

const VariablesConfigurator = ({ variables = {}, onChange }) => {
  const variablesArray = Object.entries(variables).map(([key, value]) => ({ key, value }));
  
  const handleAdd = () => {
    const tempKey = `_new_${Date.now()}`;
    onChange({ ...variables, [tempKey]: '' });
  };

  const handleRemove = (index) => {
    const newVariables = { ...variables };
    delete newVariables[variablesArray[index].key];
    onChange(newVariables);
  };

  const handleChange = (index, field, newValue) => {
    const oldKey = variablesArray[index].key;
    const newVariables = { ...variables };
    
    if (field === 'key') {
      delete newVariables[oldKey];
      const finalKey = newValue || `_new_${Date.now()}`;
      newVariables[finalKey] = variables[oldKey] || '';
    } else {
      newVariables[oldKey] = newValue;
    }
    
    onChange(newVariables);
  };

  const columns = [
    {
      title: '变量名',
      dataIndex: 'key',
      width: '40%',
      render: (text, record, index) => (
        <Input
          value={text.startsWith('_new_') ? '' : text}
          placeholder="例如: base_url"
          onChange={(e) => handleChange(index, 'key', e.target.value)}
        />
      ),
    },
    {
      title: '变量值',
      dataIndex: 'value',
      width: '50%',
      render: (text, record, index) => (
        <Input
          value={text}
          placeholder="例如: https://api.example.com"
          onChange={(e) => handleChange(index, 'value', e.target.value)}
        />
      ),
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

  return (
    <div>
      <Table
        columns={columns}
        dataSource={variablesArray}
        pagination={false}
        size="small"
        rowKey={(record, index) => record.key + '_' + index} // 确保唯一性
        locale={{ emptyText: '暂无变量，点击下方按钮添加' }}
      />
      <Button 
        size="small" 
        style={{ marginBottom: 8 }} 
        onClick={handleAdd}
      >
        <PlusOutlined /> 添加变量
      </Button>
    </div>
  );
};

export default VariablesConfigurator;