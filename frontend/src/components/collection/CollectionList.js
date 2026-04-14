import React from 'react';
import { Table, Button, Space, Tooltip, Tag, Popconfirm } from 'antd';
import { EditOutlined, PlayCircleOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';

const CollectionList = ({
  collections = [],
  loading = false,
  executing = new Set(),
  onEdit,
  onExecute,
  onDelete,
}) => {
  const getModeTag = (mode) => {
    const modeConfig = {
      concurrent: { color: 'blue', text: '并发' },
      sequential: { color: 'green', text: '顺序' },
      chain: { color: 'purple', text: '链式' },
    };
    const config = modeConfig[mode] || { color: 'default', text: mode };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '模式',
      dataIndex: 'execution_mode',
      key: 'execution_mode',
      width: 100,
      render: getModeTag,
    },
    {
      title: '请求数',
      dataIndex: 'request_count',
      key: 'request_count',
      align: 'center',
      width: 80,
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
            />
          </Tooltip>
          <Tooltip title="执行">
            <Button
              type="text"
              icon={executing.has(record.id) ? <LoadingOutlined /> : <PlayCircleOutlined style={{ color: '#52c41a' }} />}
              loading={executing.has(record.id)}
              onClick={() => onExecute(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除该集合？"
            onConfirm={() => onDelete(record.id)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={collections}
      rowKey="id"
      loading={loading}
      pagination={{ pageSize: 10 }}
    />
  );
};

export default CollectionList;