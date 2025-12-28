import React, { useEffect, useState, useCallback } from 'react';
import apiClient from '../api/axios';
import { Table, Button, Space, Input, Modal, Form, Typography, Popconfirm, notification, Descriptions, Select } from 'antd';

const { Title } = Typography;
const { Option } = Select;

function FeatureTestCaseManager() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [viewing, setViewing] = useState(null);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/feature-tests/');
      setData(res.data.results || []);
    } catch (e) {
      notification.error({ message: '获取功能测试用例失败', description: e.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (record) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await apiClient.delete(`/feature-tests/${id}/`);
      notification.success({ message: '已删除' });
      fetchList();
    } catch (e) {
      notification.error({ message: '删除失败', description: e.message });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        const res = await apiClient.patch(`/feature-tests/${editing.id}/`, values);
        if (res.status === 200) notification.success({ message: '已更新' });
      } else {
        const res = await apiClient.post('/feature-tests/', values);
        if (res.status === 201) notification.success({ message: '已创建' });
      }
      setModalOpen(false);
      fetchList();
    } catch (e) {
      // antd form validation errors are not network errors
      if (e?.message) {
        notification.error({ message: '保存失败', description: e.message });
      }
    }
  };

  const wrap = (text) => (<div style={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>{text}</div>);

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', render: wrap },
    { title: '版本号', dataIndex: 'version', key: 'version', render: wrap },
    { title: '是否通过', dataIndex: 'is_passed', key: 'is_passed', render: (val) => {
      if (val === true) return <span style={{ color: '#52c41a' }}>✅ 通过</span>;
      if (val === false) return <span style={{ color: '#ff4d4f' }}>❌ 未通过</span>;
      if (val === null || val === 'null') return <span style={{ color: 'gray' }}>⏸️ 未测试</span>;
      return wrap(val);
    } },
    { title: '待确定', dataIndex: 'to_confirm', key: 'to_confirm', render: wrap },
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', render: (t) => t ? new Date(t).toLocaleString() : '' },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button onClick={() => setViewing(record)}>查看</Button>
          <Button onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此用例？" onConfirm={() => handleDelete(record.id)}>
            <Button danger>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const filtered = data.filter(item => !search || (item.title || '').toLowerCase().includes(search.toLowerCase()));

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Title level={2}>功能测试用例</Title>
      <Space>
        <Input placeholder="按标题搜索" value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 240 }} />
        <Button type="primary" onClick={openCreate}>新增用例</Button>
        <Button onClick={fetchList}>刷新</Button>
      </Space>

      <Table
        columns={columns}
        dataSource={filtered}
        loading={loading}
        rowKey="id"
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editing ? '编辑用例' : '新增用例'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={800}
        destroyOnClose
      >
        <Form layout="vertical" form={form} preserve={false}>
          <Form.Item
            name="title"
            label="测试标题"
            rules={[
              { required: true, message: '请输入标题' },
              { max: 200, message: '标题不能超过200字符' }
            ]}
          >
            <Input maxLength={200} showCount />
          </Form.Item>
          <Form.Item name="pre_steps" label="前置步骤">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="steps" label="操作步骤" rules={[{ required: true, message: '请输入步骤' }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="expected_result" label="预期结果" rules={[{ required: true, message: '请输入预期结果' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="actual_result" label="实际结果">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="to_confirm" label="待确定">
            <Input />
          </Form.Item>
          <Form.Item name="is_passed" label="是否通过">
            <Select allowClear placeholder="请选择">
              <Option value={true}>✅ 通过</Option>
              <Option value={false}>❌ 未通过</Option>
              <Option value={null}>⏸️ 未测试</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="version"
            label="版本号"
            rules={[
              { max: 50, message: '版本号不能超过50字符' }
            ]}
          >
            <Input maxLength={50} showCount />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="用例详情"
        open={!!viewing}
        onOk={() => setViewing(null)}
        onCancel={() => setViewing(null)}
        okText="返回"
        cancelButtonProps={{ style: { display: 'none' } }}
        width={800}
        destroyOnClose
      >
        {viewing && (
          <Descriptions bordered column={1} size="middle">
            <Descriptions.Item label="测试标题">{viewing.title}</Descriptions.Item>
            <Descriptions.Item label="前置步骤"><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{viewing.pre_steps}</pre></Descriptions.Item>
            <Descriptions.Item label="操作步骤"><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{viewing.steps}</pre></Descriptions.Item>
            <Descriptions.Item label="预期结果"><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{viewing.expected_result}</pre></Descriptions.Item>
            <Descriptions.Item label="实际结果"><pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{viewing.actual_result}</pre></Descriptions.Item>
            <Descriptions.Item label="待确定">{viewing.to_confirm}</Descriptions.Item>
            <Descriptions.Item label="是否通过">{viewing.is_passed}</Descriptions.Item>
            <Descriptions.Item label="版本号">{viewing.version}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{viewing.created_at ? new Date(viewing.created_at).toLocaleString() : ''}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{viewing.updated_at ? new Date(viewing.updated_at).toLocaleString() : ''}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </Space>
  );
}

export default FeatureTestCaseManager;


