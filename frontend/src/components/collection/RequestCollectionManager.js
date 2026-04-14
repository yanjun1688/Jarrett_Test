import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../../api/axios';
import { Button, Card, Alert, message, Typography, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import CollectionList from './CollectionList';
import CollectionFormModal from './CollectionFormModal';
import ExecutionResultDrawer from './ExecutionResultDrawer';

const { Title, Text } = Typography;

const RequestCollectionManager = () => {
  const [collections, setCollections] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(new Set());

  const [formModalVisible, setFormModalVisible] = useState(false);
  const [editingCollection, setEditingCollection] = useState(null);

  const [resultDrawerVisible, setResultDrawerVisible] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [collectionsRes, requestsRes] = await Promise.all([
        apiClient.get('/request-collections/'),
        apiClient.get('/api-requests/'),
      ]);
      setCollections(collectionsRes.data.results || []);
      setRequests(requestsRes.data.results || []);
    } catch (error) {
      message.error('获取数据失败: ' + error.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const openCreateModal = () => {
    setEditingCollection(null);
    setFormModalVisible(true);
  };

  const openEditModal = async (record) => {
    try {
      const detailRes = await apiClient.get(`/request-collections/${record.id}/`);
      setEditingCollection(detailRes.data);
      setFormModalVisible(true);
    } catch (error) {
      message.error('加载详情失败');
    }
  };

  const closeModal = () => {
    setFormModalVisible(false);
    setEditingCollection(null);
  };

  const handleSaveCollection = async (payload, editingRecord) => {
    try {
      if (editingRecord) {
        await apiClient.patch(`/request-collections/${editingRecord.id}/`, payload);
        message.success('更新成功');
      } else {
        await apiClient.post('/request-collections/', payload);
        message.success('创建成功');
      }
      closeModal();
      loadData();
    } catch (error) {
      message.error('保存失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDelete = async (id) => {
    try {
      await apiClient.delete(`/request-collections/${id}/`);
      message.success('删除成功');
      loadData();
    } catch (error) {
      message.error('删除失败: ' + error.message);
    }
  };

  const handleExecute = async (collection) => {
    setExecuting(prev => new Set(prev).add(collection.id));
    
    try {
      const response = await apiClient.post(`/request-collections/${collection.id}/execute/`);
      const result = response.data;
      
      setExecutionResult({
        ...result,
        collection_name: collection.name,
        total_requests: collection.request_count || result.total_requests || 0,
      });
      setResultDrawerVisible(true);
      
      if (result.status === 'success') {
        message.success('执行成功');
      } else if (result.status === 'failed') {
        message.warning('执行完成，存在失败');
      }
    } catch (error) {
      message.error('执行失败: ' + error.message);
      setExecutionResult({
        status: 'failed',
        collection_name: collection.name,
        output: error.message,
        total_requests: 0,
        passed_requests: 0,
        failed_requests: 0,
      });
      setResultDrawerVisible(true);
    }
    
    setExecuting(prev => {
      const newSet = new Set(prev);
      newSet.delete(collection.id);
      return newSet;
    });
  };

  const closeResultDrawer = () => {
    setResultDrawerVisible(false);
    setExecutionResult(null);
  };

  return (
    <div className="request-collection-container">
      <Space className="request-collection-header" style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          创建请求集合
        </Button>
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>使用说明</Title>
        <Text>请求集合用于批量执行多个 API 请求，支持两种执行模式：</Text>
        <ul style={{ marginTop: 8, marginBottom: 0, paddingLeft: 20 }}>
          <li>
            <Text strong style={{ color: '#1890ff' }}>并发执行</Text>：所有请求同时发起，适合压力测试
          </li>
          <li>
            <Text strong style={{ color: '#722ed1' }}>链式执行</Text>：按顺序执行 + 变量传递
            <div style={{ paddingLeft: 20, marginTop: 4 }}>
              <Text type="secondary">使用 {'{{变量名}}'} 引用变量，从响应提取数据供后续请求使用</Text>
            </div>
          </li>
        </ul>
        <Alert
          style={{ marginTop: 12 }}
          message="Setup/Teardown 支持"
          description="可配置 Setup 前置请求（执行前运行）和 Teardown 后置请求（执行后清理）"
          type="info"
          showIcon
        />
      </Card>

      <CollectionList
        collections={collections}
        loading={loading}
        executing={executing}
        onEdit={openEditModal}
        onExecute={handleExecute}
        onDelete={handleDelete}
      />

      <CollectionFormModal
        visible={formModalVisible}
        editingRecord={editingCollection}
        requests={requests}
        onClose={closeModal}
        onSave={handleSaveCollection}
      />

      <ExecutionResultDrawer
        visible={resultDrawerVisible}
        execution={executionResult}
        onClose={closeResultDrawer}
        onReExecute={() => {
          if (editingCollection) {
            handleExecute(editingCollection);
          }
        }}
      />
    </div>
  );
};

export default RequestCollectionManager;