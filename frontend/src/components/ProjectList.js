import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/axios';
import { List, Card, Typography, Spin, Button, Space, Modal, Form, Input, notification, Popconfirm } from 'antd';
import { Link } from 'react-router-dom';

const { Title } = Typography;
const { Meta } = Card;

function ProjectList() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/projects/');
      setProjects(response.data.results || []);
    } catch (error) {
      console.error('获取项目列表失败:', error);
      notification.error({ message: '获取失败', description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const openCreateModal = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEditModal = (project) => {
    setEditing(project);
    form.setFieldsValue({
      name: project.name,
      description: project.description,
    });
    setModalOpen(true);
  };

  const handleDelete = async (projectId) => {
    try {
      await apiClient.delete(`/projects/${projectId}/`);
      notification.success({ message: '项目已删除' });
      fetchProjects();
    } catch (error) {
      notification.error({ message: '删除失败', description: error.message });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editing) {
        await apiClient.patch(`/projects/${editing.id}/`, values);
        notification.success({ message: '项目已更新' });
      } else {
        await apiClient.post('/projects/', values);
        notification.success({ message: '项目已创建' });
      }
      setModalOpen(false);
      fetchProjects();
    } catch (error) {
      notification.error({ message: '保存失败', description: error.message });
    }
  };

  return (
    <div style={{ width: '100%' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={2}>项目列表</Title>
          <Button type="primary" onClick={openCreateModal}>
            新增项目
          </Button>
        </Space>

        <List
          loading={loading}
          grid={{
            gutter: 16,
            xs: 1,
            sm: 2,
            md: 3,
            lg: 3,
            xl: 4,
            xxl: 4,
          }}
          dataSource={projects}
          renderItem={(project) => (
            <List.Item>
              <Card
                hoverable
                title={
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Link to={`/projects/${project.id}`}>{project.name}</Link>
                    <Space>
                      <Button size="small" onClick={() => openEditModal(project)}>编辑</Button>
                      <Popconfirm
                        title="确认删除此项目？"
                        onConfirm={() => handleDelete(project.id)}
                      >
                        <Button size="small" danger>删除</Button>
                      </Popconfirm>
                    </Space>
                  </Space>
                }
                style={{ width: '100%' }}
              >
                <Meta
                  description={project.description || '暂无描述'}
                />
              </Card>
            </List.Item>
          )}
        />
      </Space>

      <Modal
        title={editing ? '编辑项目' : '新增项目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          preserve={false}
          initialValues={{ name: '', description: '' }}
        >
          <Form.Item
            name="name"
            label="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input maxLength={100} showCount />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default ProjectList;
