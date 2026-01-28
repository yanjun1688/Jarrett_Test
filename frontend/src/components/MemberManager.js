import React, { useState, useEffect } from 'react';
import {
  Button,
  Modal,
  Table,
  Tag,
  Space,
  message,
  Form,
  Input,
  Select,
  Popconfirm,
  Divider,
  Typography
} from 'antd';
import { PlusOutlined, DeleteOutlined, UserOutlined } from '@ant-design/icons';
import apiClient from '../api/axios';

const { Option } = Select;
const { Title, Text } = Typography;

const MemberManager = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userLoading, setUserLoading] = useState(false);
  const [roleLoading, setRoleLoading] = useState(false);
  const [form] = Form.useForm();

  // 获取用户列表
  const fetchUsers = async () => {
    setUserLoading(true);
    try {
      const response = await apiClient.get('/users/');
      setUsers(response.data.results || response.data);
    } catch (error) {
      message.error('获取用户列表失败');
      logger.error('Error fetching users:', error);
    } finally {
      setUserLoading(false);
    }
  };

  // 获取角色列表
  const fetchRoles = async () => {
    setRoleLoading(true);
    try {
      const response = await apiClient.get('/roles/');
      setRoles(response.data.results || response.data);
    } catch (error) {
      message.error('获取角色列表失败');
      logger.error('Error fetching roles:', error);
    } finally {
      setRoleLoading(false);
    }
  };

  // 打开弹窗
  const showModal = () => {
    setIsModalOpen(true);
    fetchUsers();
   fetchRoles();
  };

  // 关闭弹窗
  const handleCancel = () => {
    setIsModalOpen(false);
    form.resetFields();
  };

  // 创建新用户
  const handleCreateUser = async (values) => {
    setLoading(true);
    try {
      await apiClient.post('/users/', values);
      message.success('用户创建成功');
      form.resetFields();
      fetchUsers();
    } catch (error) {
      message.error('用户创建失败: ' + (error.response?.data?.error || '未知错误'));
      logger.error('Error creating user:', error);
    } finally {
      setLoading(false);
    }
  };

  // 删除用户
  const handleDeleteUser = async (userId) => {
    try {
      await apiClient.delete(`/users/${userId}/`);
      message.success('用户删除成功');
      fetchUsers();
    } catch (error) {
      message.error('用户删除失败');
      logger.error('Error deleting user:', error);
    }
  };

  // 分配角色给用户
  const handleAssignRole = async (userId, roleId) => {
    try {
      await apiClient.post(`/users/${userId}/assign-role/`, { role_id: roleId });
      message.success('角色分配成功');
      fetchUsers();
    } catch (error) {
      message.error('角色分配失败: ' + (error.response?.data?.error || '未知错误'));
      logger.error('Error assigning role:', error);
    }
  };

  // 移除用户的角色
  const handleRemoveRole = async (userId, roleId) => {
    try {
      await apiClient.delete(`/users/${userId}/remove-role/${roleId}/`);
      message.success('角色移除成功');
      fetchUsers();
    } catch (error) {
      message.error('角色移除失败');
      logger.error('Error removing role:', error);
    }
  };

  // 权限标签颜色
  const getPermissionColor = (permission) => {
    switch (permission) {
      case 'crud':
        return 'error';
      case 'view':
        return 'blue';
      default:
        return 'default';
    }
  };

  // 权限标签文本
  const getPermissionText = (permission) => {
    switch (permission) {
      case 'crud':
        return '增删改查';
      case 'view':
        return '仅查看';
      default:
        return permission;
    }
  };

  // 用户表格列定义
  const userColumns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 150,
      fixed: 'left',
    },
    {
      title: '姓名',
      key: 'full_name',
      width: 120,
      render: (record) => `${record.first_name || ''} ${record.last_name || ''}`.trim() || '-',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      ellipsis: true,
    },
    {
      title: '角色',
      key: 'roles',
      width: 200,
      render: (record) => {
        const userRoles = record.roles || [];
        if (userRoles.length === 0) {
          return <Text type="secondary">-</Text>;
        }
        return (
          <Space wrap size={[0, 4]}>
            {userRoles.map(role => (
              <Tag
                key={role.id}
                color={getPermissionColor(role.permission)}
                closable
                onClose={() => handleRemoveRole(record.id, role.id)}
                style={{ marginBottom: 4 }}
              >
                {role.name}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (record) => (
        <Space size="small">
          <Select
            size="small"
            placeholder="分配角色"
            style={{ width: 120 }}
            loading={roleLoading}
            disabled={roleLoading}
            allowClear
            onSelect={(value) => handleAssignRole(record.id, value)}
          >
            {roles.map(role => (
              <Option key={role.id} value={role.id}>
                {role.name}（{getPermissionText(role.permission)}）
              </Option>
            ))}
          </Select>
          <Popconfirm
            title="确定删除这个用户吗？"
            onConfirm={() => handleDeleteUser(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              size="small"
              icon={<DeleteOutlined />}
              disabled={record.username === 'admin'}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  useEffect(() => {
    if (isModalOpen) {
      fetchUsers();
      fetchRoles();
    }
  }, [isModalOpen]);

  return (
    <>
      <Button
        type="primary"
        icon={<UserOutlined />}
        onClick={showModal}
        style={{ margin: '0 8px' }}
      >
        成员管理
      </Button>

      <Modal
        title="成员与权限管理"
        open={isModalOpen}
        onCancel={handleCancel}
        footer={null}
        width={1000}
        style={{ top: 50 }}
        bodyStyle={{
          maxHeight: '70vh',
          overflow: 'auto',
          padding: '24px'
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 创建新用户表单 */}
          <div style={{
            padding: '16px',
            background: '#f5f5f5',
            borderRadius: '8px',
            boxSizing: 'border-box'
          }}>
            <Title level={5} style={{ marginBottom: 16 }}>创建新用户</Title>
            <Form
              form={form}
              layout="inline"
              onFinish={handleCreateUser}
              style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}
            >
              <Form.Item
                name="username"
                rules={[{ required: true, message: '请输入用户名' }]}
                style={{ flex: '1 1 200px', minWidth: '200px' }}
              >
                <Input placeholder="用户名" />
              </Form.Item>
              <Form.Item
                name="password"
                rules={[{ required: true, message: '请输入密码' }]}
                style={{ flex: '1 1 200px', minWidth: '200px' }}
              >
                <Input.Password placeholder="密码" />
              </Form.Item>
              <Form.Item
                name="email"
                style={{ flex: '1 1 200px', minWidth: '200px' }}
              >
                <Input placeholder="邮箱（可选）" />
              </Form.Item>
              <Form.Item
                name="first_name"
                style={{ flex: '1 1 150px', minWidth: '150px' }}
              >
                <Input placeholder="名字（可选）" />
              </Form.Item>
              <Form.Item
                name="last_name"
                style={{ flex: '1 1 150px', minWidth: '150px' }}
              >
                <Input placeholder="姓氏（可选）" />
              </Form.Item>
              <Form.Item
                name="role_ids"
                style={{ flex: '1 1 250px', minWidth: '250px' }}
              >
                <Select
                  mode="multiple"
                  placeholder="选择角色（可选）"
                  loading={roleLoading}
                  allowClear
                >
                  {roles.map(role => (
                    <Option key={role.id} value={role.id}>
                      {role.name}（{getPermissionText(role.permission)}）
                    </Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item style={{ flex: '0 0 auto', marginLeft: 'auto' }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  icon={<PlusOutlined />}
                >
                  创建用户
                </Button>
              </Form.Item>
            </Form>
          </div>

          <Divider style={{ margin: 0 }} />

          {/* 用户列表 */}
          <div>
            <Title level={5} style={{ marginBottom: 16 }}>用户列表</Title>
            <Table
              columns={userColumns}
              dataSource={users}
              rowKey="id"
              loading={userLoading}
              size="small"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
              scroll={{ x: 'max-content' }}
              bordered
            />
          </div>
        </Space>
      </Modal>
    </>
  );
};

export default MemberManager;
