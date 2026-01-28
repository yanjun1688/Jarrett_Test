import React from 'react';
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd';
import { DeleteOutlined, EditOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';

/**
 * 步骤编辑器组件
 * 
 * @param {object} props
 * @param {array} props.steps - 步骤列表
 * @param {function} props.onUpdate - 更新步骤回调 (steps) => void
 * @param {function} props.onEdit - 编辑步骤回调 (step, index) => void
 */
const StepEditor = ({ steps = [], onUpdate, onEdit }) => {
  // 删除步骤
  const handleDelete = (index) => {
    const newSteps = [...steps];
    newSteps.splice(index, 1);
    // 重新排序
    newSteps.forEach((step, idx) => {
      step.order = idx + 1;
    });
    onUpdate(newSteps);
    message.success('步骤已删除');
  };

  // 上移步骤
  const handleMoveUp = (index) => {
    if (index === 0) return;
    const newSteps = [...steps];
    [newSteps[index - 1], newSteps[index]] = [newSteps[index], newSteps[index - 1]];
    // 重新排序
    newSteps.forEach((step, idx) => {
      step.order = idx + 1;
    });
    onUpdate(newSteps);
  };

  // 下移步骤
  const handleMoveDown = (index) => {
    if (index === steps.length - 1) return;
    const newSteps = [...steps];
    [newSteps[index], newSteps[index + 1]] = [newSteps[index + 1], newSteps[index]];
    // 重新排序
    newSteps.forEach((step, idx) => {
      step.order = idx + 1;
    });
    onUpdate(newSteps);
  };

  const columns = [
    {
      title: '序号',
      dataIndex: 'order',
      key: 'order',
      width: 60,
      align: 'center',
    },
    {
      title: '操作类型',
      dataIndex: 'action_type',
      key: 'action_type',
      width: 120,
      render: (type) => {
        // MVP只支持三种操作类型
        const typeMap = {
          navigate: { text: '导航', color: 'blue' },
          click: { text: '点击', color: 'green' },
          fill: { text: '填写', color: 'orange' },
        };
        const config = typeMap[type] || { text: type || '未知', color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '定位器',
      key: 'locator',
      width: 200,
      render: (_, record) => {
        const locator = record.element_locator || record.locator;
        if (!locator) return '-';
        return (
          <Tag>
            {locator.locator_type || locator.type}: {locator.locator_value || locator.value}
          </Tag>
        );
      },
    },
    {
      title: '参数',
      key: 'params',
      width: 150,
      render: (_, record) => {
        const params = record.action_params || record.params;
        if (!params || Object.keys(params).length === 0) return '-';
        return (
          <div style={{ fontSize: '12px' }}>
            {Object.entries(params).map(([key, value]) => (
              <div key={key}>
                <strong>{key}:</strong> {String(value).substring(0, 20)}
                {String(value).length > 20 ? '...' : ''}
              </div>
            ))}
          </div>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right',
      render: (_, record, index) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => onEdit && onEdit(record, index)}
          >
            编辑
          </Button>
          <Button
            size="small"
            icon={<ArrowUpOutlined />}
            disabled={index === 0}
            onClick={() => handleMoveUp(index)}
          />
          <Button
            size="small"
            icon={<ArrowDownOutlined />}
            disabled={index === steps.length - 1}
            onClick={() => handleMoveDown(index)}
          />
          <Popconfirm
            title="确定删除此步骤吗？"
            onConfirm={() => handleDelete(index)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={steps.map((step, index) => ({ ...step, key: step.id || index }))}
      pagination={false}
      scroll={{ x: 1000 }}
      size="small"
    />
  );
};

export default StepEditor;

