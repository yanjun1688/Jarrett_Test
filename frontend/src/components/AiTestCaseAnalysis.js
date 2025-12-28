import React, { useState, useEffect } from 'react';
import {
  Card,
  Upload,
  Button,
  Space,
  Typography,
  Table,
  Tag,
  Collapse,
  Descriptions,
  message,
  Spin,
  Empty,
  Modal,
  Form,
  Input,
  Checkbox,
  Divider,
} from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  SettingOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { processPRD } from '../api/aiAgent';
import { featureTestsAPI } from '../api/featureTests';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;
const STORAGE_KEY = 'ai_analysis_config';

function AiTestCaseAnalysis() {
  const [loading, setLoading] = useState(false);
  const [testSuites, setTestSuites] = useState([]);
  const [fileList, setFileList] = useState([]);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [configForm] = Form.useForm();
  const [selectedTestCases, setSelectedTestCases] = useState(new Set());
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveForm] = Form.useForm();

  // 加载配置
  useEffect(() => {
    const savedConfig = localStorage.getItem(STORAGE_KEY);
    if (!savedConfig) {
      // 如果没有保存的配置，显示配置弹窗
      setConfigModalVisible(true);
    } else {
      try {
        const config = JSON.parse(savedConfig);
        configForm.setFieldsValue(config);
      } catch (e) {
        console.error('Failed to load config:', e);
      }
    }
  }, [configForm]);

  // 获取配置
  const getConfig = () => {
    const savedConfig = localStorage.getItem(STORAGE_KEY);
    if (savedConfig) {
      try {
        return JSON.parse(savedConfig);
      } catch (e) {
        return null;
      }
    }
    return null;
  };

  // 保存配置
  const handleSaveConfig = () => {
    configForm.validateFields().then((values) => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(values));
      message.success('配置已保存');
      setConfigModalVisible(false);
    }).catch((error) => {
      console.error('Config validation failed:', error);
    });
  };

  // 处理文件上传和分析
  const handleProcessPRD = async (file) => {
    if (!file) {
      message.warning('请先选择文件');
      return;
    }

    // 检查配置
    const config = getConfig();
    if (!config || !config.api_key || !config.api_key.trim()) {
      message.error('请先配置有效的 Key 和 Value');
      setConfigModalVisible(true);
      return;
    }

    setLoading(true);
    setTestSuites([]);
    setSelectedTestCases(new Set());

    try {
      const response = await processPRD(file, config.api_key);
      
      if (response.success && response.data && response.data.test_suites) {
        setTestSuites(response.data.test_suites);
        message.success(`成功生成 ${response.data.test_suites_count} 个测试套件`);
      } else {
        message.error('处理失败：未返回测试用例数据');
      }
    } catch (error) {
      console.error('处理PRD失败:', error);
      message.error(
        error.response?.data?.error || error.message || '处理PRD文档失败，请检查文件格式和网络连接'
      );
    } finally {
      setLoading(false);
    }
  };

  // 文件上传配置
  const uploadProps = {
    accept: '.pdf,.doc,.docx,.txt',
    fileList,
    beforeUpload: (file) => {
      // 阻止自动上传
      return false;
    },
    onChange: (info) => {
      setFileList(info.fileList);
    },
    onRemove: () => {
      setFileList([]);
      setTestSuites([]);
      setSelectedTestCases(new Set());
    },
    maxCount: 1,
  };

  // 处理复选框选择
  const handleCheckboxChange = (suiteIndex, caseIndex, checked) => {
    const key = `${suiteIndex}-${caseIndex}`;
    const newSelected = new Set(selectedTestCases);
    if (checked) {
      newSelected.add(key);
    } else {
      newSelected.delete(key);
    }
    setSelectedTestCases(newSelected);
  };

  // 处理全选/取消全选
  const handleSelectAll = (suiteIndex, checked) => {
    const newSelected = new Set(selectedTestCases);
    const suite = testSuites[suiteIndex];
    if (suite && suite.test_cases) {
      suite.test_cases.forEach((_, caseIndex) => {
        const key = `${suiteIndex}-${caseIndex}`;
        if (checked) {
          newSelected.add(key);
        } else {
          newSelected.delete(key);
        }
      });
    }
    setSelectedTestCases(newSelected);
  };

  // 打开保存弹窗
  const handleOpenSaveModal = () => {
    if (selectedTestCases.size === 0) {
      message.warning('请至少选择一个测试用例');
      return;
    }
    setSaveModalVisible(true);
    saveForm.resetFields();
  };

  // 保存到功能测试模块
  const handleSaveToFeatureTests = async () => {
    try {
      const values = await saveForm.validateFields();
      const version = values.version || '';

      // 收集选中的测试用例
      const testCasesToSave = [];
      testSuites.forEach((suite, suiteIndex) => {
        if (suite.test_cases) {
          suite.test_cases.forEach((testCase, caseIndex) => {
            const key = `${suiteIndex}-${caseIndex}`;
            if (selectedTestCases.has(key)) {
              // 将AI生成的测试用例转换为功能测试用例格式
              testCasesToSave.push({
                title: testCase.title,
                pre_steps: testCase.preconditions || '',
                steps: Array.isArray(testCase.steps) 
                  ? testCase.steps.map((step, idx) => `${idx + 1}. ${step}`).join('\n')
                  : testCase.steps || '',
                expected_result: testCase.expected_result || '',
                version: version,
              });
            }
          });
        }
      });

      // 批量保存
      const savePromises = testCasesToSave.map((testCase) =>
        featureTestsAPI.create(testCase)
      );

      await Promise.all(savePromises);
      message.success(`成功保存 ${testCasesToSave.length} 个测试用例到功能测试模块`);
      setSaveModalVisible(false);
      setSelectedTestCases(new Set());
    } catch (error) {
      console.error('保存失败:', error);
      message.error('保存失败：' + (error.message || '未知错误'));
    }
  };

  // 测试用例表格列定义（带复选框）
  const getTestCaseColumns = (suiteIndex) => [
    {
      title: (
        <Checkbox
          checked={
            testSuites[suiteIndex]?.test_cases?.every((_, caseIndex) =>
              selectedTestCases.has(`${suiteIndex}-${caseIndex}`)
            ) && testSuites[suiteIndex]?.test_cases?.length > 0
          }
          indeterminate={
            testSuites[suiteIndex]?.test_cases?.some((_, caseIndex) =>
              selectedTestCases.has(`${suiteIndex}-${caseIndex}`)
            ) &&
            !testSuites[suiteIndex]?.test_cases?.every((_, caseIndex) =>
              selectedTestCases.has(`${suiteIndex}-${caseIndex}`)
            )
          }
          onChange={(e) => handleSelectAll(suiteIndex, e.target.checked)}
        />
      ),
      key: 'checkbox',
      width: 60,
      render: (_, record, caseIndex) => (
        <Checkbox
          checked={selectedTestCases.has(`${suiteIndex}-${caseIndex}`)}
          onChange={(e) => handleCheckboxChange(suiteIndex, caseIndex, e.target.checked)}
        />
      ),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority) => {
        const colorMap = {
          High: 'red',
          Medium: 'orange',
          Low: 'green',
        };
        return <Tag color={colorMap[priority] || 'default'}>{priority}</Tag>;
      },
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (category) => category || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  // 展开行配置 - 显示测试用例详情
  const expandedRowRender = (record) => {
    return (
      <div style={{ padding: '16px', background: '#fafafa' }}>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="描述">
            <Paragraph>{record.description}</Paragraph>
          </Descriptions.Item>
          {record.preconditions && (
            <Descriptions.Item label="前置条件">
              <Text>{record.preconditions}</Text>
            </Descriptions.Item>
          )}
          <Descriptions.Item label="测试步骤">
            <ol style={{ margin: 0, paddingLeft: '20px' }}>
              {record.steps && record.steps.map((step, index) => (
                <li key={index} style={{ marginBottom: '8px' }}>
                  <Text>{step}</Text>
                </li>
              ))}
            </ol>
          </Descriptions.Item>
          <Descriptions.Item label="预期结果">
            <Text>{record.expected_result}</Text>
          </Descriptions.Item>
        </Descriptions>
      </div>
    );
  };

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <FileTextOutlined style={{ marginRight: '8px' }} />
        AI分析用例
      </Title>
      <Paragraph type="secondary">
        上传PRD文档（PDF/Word/TXT），AI将自动分析并生成测试用例
      </Paragraph>

      {/* 配置弹窗 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>AI模型配置</span>
          </Space>
        }
        open={configModalVisible}
        onOk={handleSaveConfig}
        onCancel={() => {
          const config = getConfig();
          if (config && config.api_key) {
            setConfigModalVisible(false);
          } else {
            message.warning('请先配置有效的 Key 和 Value');
          }
        }}
        okText="保存配置"
        cancelText="跳过"
        width={600}
      >
        <Form form={configForm} layout="vertical">
          <Form.Item
            name="api_key"
            label="API Key"
            rules={[
              { required: true, message: '请输入API Key' },
              { min: 10, message: 'API Key长度至少10个字符' },
            ]}
          >
            <Input.Password placeholder="请输入OpenAI API Key" />
          </Form.Item>
          <Form.Item name="api_value" label="API Value (可选)">
            <Input placeholder="可选：API Value或其他配置参数" />
          </Form.Item>
          <Paragraph type="secondary" style={{ marginTop: '16px' }}>
            <Text type="warning">注意：</Text>配置信息将保存在浏览器本地存储中，不会上传到服务器。
          </Paragraph>
        </Form>
      </Modal>

      <Card style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>选择PRD文档</Button>
            </Upload>
            <Button
              type="primary"
              size="large"
              icon={loading ? <LoadingOutlined /> : <CheckCircleOutlined />}
              onClick={() => {
                const file = fileList[0]?.originFileObj;
                if (file) {
                  handleProcessPRD(file);
                } else {
                  message.warning('请先选择文件');
                }
              }}
              loading={loading}
              disabled={loading || fileList.length === 0}
            >
              {loading ? 'AI分析中...' : '开始分析'}
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setConfigModalVisible(true)}
            >
              配置
            </Button>
            {testSuites.length > 0 && (
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleOpenSaveModal}
                disabled={selectedTestCases.size === 0}
              >
                保存选中项 ({selectedTestCases.size})
              </Button>
            )}
          </Space>
        </Space>
      </Card>

      {loading && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Text>AI正在分析PRD文档，请稍候...</Text>
            </div>
          </div>
        </Card>
      )}

      {!loading && testSuites.length > 0 && (
        <div>
          <Title level={3}>生成的测试用例</Title>
          <Paragraph type="secondary">
            请勾选需要保存到功能测试模块的测试用例，然后点击"保存选中项"按钮
          </Paragraph>
          <Collapse defaultActiveKey={['0']} style={{ marginBottom: '16px' }}>
            {testSuites.map((suite, suiteIndex) => (
              <Panel
                header={
                  <Space>
                    <Text strong>{suite.name}</Text>
                    <Tag>{suite.test_cases?.length || 0} 个测试用例</Tag>
                    <Tag color="blue">
                      已选 {suite.test_cases?.filter((_, caseIndex) =>
                        selectedTestCases.has(`${suiteIndex}-${caseIndex}`)
                      ).length || 0} 个
                    </Tag>
                  </Space>
                }
                key={suiteIndex}
              >
                {suite.description && (
                  <Paragraph type="secondary" style={{ marginBottom: '16px' }}>
                    {suite.description}
                  </Paragraph>
                )}
                <Table
                  columns={getTestCaseColumns(suiteIndex)}
                  dataSource={suite.test_cases?.map((tc, index) => ({
                    ...tc,
                    key: `${suiteIndex}-${index}`,
                  }))}
                  pagination={false}
                  expandable={{
                    expandedRowRender,
                    expandRowByClick: true,
                  }}
                  size="small"
                />
              </Panel>
            ))}
          </Collapse>
        </div>
      )}

      {!loading && testSuites.length === 0 && fileList.length > 0 && (
        <Card>
          <Empty description="暂无测试用例数据，请点击'开始分析'按钮" />
        </Card>
      )}

      {/* 保存到功能测试模块的弹窗 */}
      <Modal
        title="保存到功能测试模块"
        open={saveModalVisible}
        onOk={handleSaveToFeatureTests}
        onCancel={() => setSaveModalVisible(false)}
        okText="保存"
        cancelText="取消"
        width={500}
      >
        <Form form={saveForm} layout="vertical">
          <Form.Item
            name="version"
            label="版本号（可选）"
            rules={[{ max: 50, message: '版本号不能超过50字符' }]}
          >
            <Input placeholder="例如：v1.0.0" maxLength={50} />
          </Form.Item>
          <Paragraph type="secondary">
            将保存 <Text strong>{selectedTestCases.size}</Text> 个选中的测试用例到功能测试模块
          </Paragraph>
        </Form>
      </Modal>
    </div>
  );
}

export default AiTestCaseAnalysis;
