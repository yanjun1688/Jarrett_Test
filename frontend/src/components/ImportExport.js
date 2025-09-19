import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Button, InputNumber, Card, Space, Typography, Divider, notification } from 'antd';
import { UploadOutlined, DownloadOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

function ImportExport() {
  const [importFile, setImportFile] = useState(null);
  const [importProjectId, setImportProjectId] = useState(null);
  const [exportProjectId, setExportProjectId] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleImport = async () => {
    if (!importFile || !importProjectId) {
      notification.error({ message: '请选择文件并输入项目ID' });
      return;
    }

    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('project_id', importProjectId);

    setIsImporting(true);
    try {
      const response = await axios.post('http://localhost:8000/api/import-testcases/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      notification.success({ message: '导入成功', description: response.data.message });
    } catch (error) {
      notification.error({ message: '导入失败', description: error.response?.data?.error || '发生未知错误' });
    } finally {
      setIsImporting(false);
    }
  };

  const handleExport = async () => {
    if (!exportProjectId) {
      notification.error({ message: '请输入要导出的项目ID' });
      return;
    }

    setIsExporting(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/export-testcases/?project_id=${exportProjectId}`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `testcases_project_${exportProjectId}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      notification.success({ message: '导出任务已开始' });
    } catch (error) {
      notification.error({ message: '导出失败', description: '无法下载文件或项目不存在' });
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    setIsDownloading(true);
    try {
      const response = await axios.get('http://localhost:8000/api/import-template/', {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'testcase_import_template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      notification.error({ message: '模板下载失败', description: error.message });
    } finally {
      setIsDownloading(false);
    }
  };

  const uploadProps = {
    beforeUpload: file => {
      setImportFile(file);
      return false; // Prevent automatic upload
    },
    onRemove: () => {
      setImportFile(null);
    },
    maxCount: 1,
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={2}>导入 / 导出</Title>

      <Card title="导入测试用例">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text>第一步：下载模板文件，根据模板格式填写测试用例。</Text>
          <Button onClick={handleDownloadTemplate} loading={isDownloading}>下载导入模板</Button>
          <Divider />
          <Text>第二步：指定要导入的项目ID，并选择已填写好的模板文件。</Text>
          <InputNumber placeholder="请输入项目ID" value={importProjectId} onChange={setImportProjectId} style={{ width: '100%' }} />
          <Upload {...uploadProps}>
            <Button icon={<UploadOutlined />}>选择文件</Button>
          </Upload>
          <Divider />
          <Text>第三步：开始导入。</Text>
          <Button type="primary" onClick={handleImport} loading={isImporting} disabled={!importFile || !importProjectId}>
            开始导入
          </Button>
        </Space>
      </Card>

      <Card title="导出测试用例">
        <Space>
          <InputNumber placeholder="请输入项目ID" value={exportProjectId} onChange={setExportProjectId} />
          <Button type="primary" icon={<DownloadOutlined />} onClick={handleExport} loading={isExporting}>
            导出
          </Button>
        </Space>
      </Card>
    </Space>
  );
}

export default ImportExport;
