import React, { useState, useEffect } from 'react';
import {
  Modal,
  Button,
  Input,
  List,
  Card,
  Space,
  Typography,
  Alert,
  Steps,
  message,
  Tag,
  Popconfirm,
  Spin
} from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  DeleteOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ApiOutlined
} from '@ant-design/icons';
import { pageStructureAPI } from '../api/pageStructure';

const { Text, Title } = Typography;

/**
 * 页面结构编辑器组件
 * 用于解析HTML、编辑元素、保存到知识库
 */
const PageStructureEditor = ({
  visible,
  onCancel,
  onSuccess,
  projectId,
  url,
  title = ''
}) => {
  // 步骤状态: 'input' | 'parse' | 'edit' | 'save'
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  
  // 数据状态
  const [parsedElements, setParsedElements] = useState([]);
  const [pageTitle, setPageTitle] = useState(title);
  const [pageUrl, setPageUrl] = useState(url || '');
  
  // 错误提示
  const [error, setError] = useState(null);

  // 重置状态当modal打开时
  useEffect(() => {
    if (visible) {
      setCurrentStep(0);
      setParsedElements([]);
      setPageTitle(title);
      setPageUrl(url || '');
      setError(null);
    }
  }, [visible, title, url]);

  // 步骤配置
  const steps = [
    {
      title: '提取元素',
      icon: <ApiOutlined />,
      description: '输入URL自动提取'
    },
    {
      title: '编辑确认',
      icon: <EditOutlined />,
      description: '增删改查页面元素'
    },
    {
      title: '保存入库',
      icon: <SaveOutlined />,
      description: '保存到知识库'
    }
  ];

  // 自动提取元素（使用 Playwright 渲染页面）
  const handleAutoExtract = async () => {
    if (!pageUrl.trim()) {
      message.error('请先输入页面URL');
      return;
    }

    setExtracting(true);
    setError(null);

    try {
      const result = await pageStructureAPI.extractElements({
        url: pageUrl,
        wait_for_network: true,
      });

      if (result.success && result.data.elements) {
        setParsedElements(result.data.elements);
        setPageTitle(result.data.title || title);
        setCurrentStep(2);
        message.success(`自动提取 ${result.data.elements.length} 个交互元素`);
      } else {
        throw new Error(result.error || '提取失败');
      }
    } catch (err) {
      setError('自动提取失败: ' + err.message);
      console.error('Extract error:', err);
    } finally {
      setExtracting(false);
    }
  };

  // 保存到知识库

  // 保存到知识库
  const handleSave = async () => {
    if (!pageUrl.trim()) {
      message.error('请输入页面URL');
      return;
    }

    if (!projectId) {
      message.error('缺少项目ID');
      return;
    }

    if (parsedElements.length === 0) {
      message.error('没有可保存的元素');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = {
        project_id: projectId,
        url: pageUrl,
        title: pageTitle,
        elements: parsedElements
      };

      const result = await pageStructureAPI.savePageStructure(data);
      
      if (result.success) {
        message.success('页面结构保存成功！');
        setCurrentStep(3); // 完成步骤
        if (onSuccess) {
          onSuccess(result.data);
        }
      } else {
        throw new Error(result.error || '保存失败');
      }
    } catch (err) {
      setError('保存失败: ' + err.message);
      console.error('Save error:', err);
    } finally {
      setLoading(false);
    }
  };

  // 更新元素
  const updateElement = (index, field, value) => {
    const newElements = [...parsedElements];
    if (field.includes('.')) {
      // 处理嵌套属性，如 attributes.id
      const [parent, child] = field.split('.');
      newElements[index][parent] = {
        ...newElements[index][parent],
        [child]: value
      };
    } else {
      newElements[index][field] = value;
    }
    setParsedElements(newElements);
  };

  // 删除元素
  const deleteElement = (index) => {
    const newElements = parsedElements.filter((_, i) => i !== index);
    setParsedElements(newElements);
    message.success('元素已删除');
  };

  // 添加新元素
  const addElement = () => {
    const newElement = {
      type: 'input',
      tag: 'input',
      attributes: {},
      text: '',
      selector_hints: []
    };
    setParsedElements([...parsedElements, newElement]);
  };

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // 提取元素
        return (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Alert
              message="自动提取页面元素"
              description="输入页面URL，系统将使用Playwright自动渲染页面并提取交互元素"
              type="info"
              showIcon
            />
            
            <div>
              <Text strong>页面URL：</Text>
              <Input
                placeholder="https://www.example.com"
                value={pageUrl}
                onChange={(e) => setPageUrl(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </div>
            
            <div>
              <Text strong>页面标题（可选）：</Text>
              <Input
                placeholder="页面标题"
                value={pageTitle}
                onChange={(e) => setPageTitle(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </div>

            {error && (
              <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} />
            )}

            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={() => {
                setCurrentStep(1);
                handleAutoExtract();
              }}
              loading={extracting}
              disabled={!pageUrl.trim()}
              block
            >
              开始提取
            </Button>
          </Space>
        );

      case 1: // 提取中
        return (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
            <p style={{ marginTop: 16 }}>正在提取页面元素...</p>
          </div>
        );

      case 2: // 编辑元素
        return (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div style={{ marginBottom: 16 }}>
              <Text strong>共 {parsedElements.length} 个交互元素</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                （可编辑、删除或添加新元素）
              </Text>
            </div>

            {error && (
              <Alert message={error} type="error" showIcon closable onClose={() => setError(null)} />
            )}

            <List
              dataSource={parsedElements}
              renderItem={(element, index) => (
                <List.Item
                  actions={[
                    <Popconfirm
                      title="确定删除此元素？"
                      onConfirm={() => deleteElement(index)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button icon={<DeleteOutlined />} danger size="small" />
                    </Popconfirm>
                  ]}
                >
                  <Card size="small" style={{ width: '100%' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Tag color="blue">{element.type}</Tag>
                        <Tag>{element.tag}</Tag>
                      </Space>
                      
                      {/* 文本内容 */}
                      {element.type !== 'input' && (
                        <div>
                          <Text type="secondary">文本内容：</Text>
                          <Input
                            size="small"
                            value={element.text || ''}
                            onChange={(e) => updateElement(index, 'text', e.target.value)}
                            placeholder="元素文本"
                          />
                        </div>
                      )}
                      
                      {/* Placeholder */}
                      {element.attributes?.placeholder && (
                        <div>
                          <Text type="secondary">Placeholder：</Text>
                          <Input
                            size="small"
                            value={element.attributes.placeholder}
                            onChange={(e) => updateElement(index, 'attributes.placeholder', e.target.value)}
                          />
                        </div>
                      )}
                      
                      {/* ID */}
                      {element.attributes?.id && (
                        <div>
                          <Text type="secondary">ID：</Text>
                          <Input
                            size="small"
                            value={element.attributes.id}
                            onChange={(e) => updateElement(index, 'attributes.id', e.target.value)}
                          />
                        </div>
                      )}
                      
                      {/* Name */}
                      {element.attributes?.name && (
                        <div>
                          <Text type="secondary">Name：</Text>
                          <Input
                            size="small"
                            value={element.attributes.name}
                            onChange={(e) => updateElement(index, 'attributes.name', e.target.value)}
                          />
                        </div>
                      )}

                      {/* 选择器提示 */}
                      <div>
                        <Text type="secondary">选择器提示：</Text>
                        <div>
                          {element.selector_hints?.map((hint, i) => (
                            <Tag key={i} size="small" style={{ margin: '2px' }}>
                              {hint}
                            </Tag>
                          ))}
                        </div>
                      </div>
                    </Space>
                  </Card>
                </List.Item>
              )}
            />

            <Button
              icon={<PlusOutlined />}
              onClick={addElement}
              block
              style={{ marginTop: 16 }}
            >
              添加元素
            </Button>

            <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 24 }}>
              <Button onClick={() => setCurrentStep(0)}>
                上一步
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={loading}
              >
                保存到知识库
              </Button>
            </Space>
          </Space>
        );

      case 3: // 完成
        return (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a' }} />
            <Title level={4} style={{ marginTop: 24 }}>
              页面结构保存成功！
            </Title>
            <Text type="secondary">
              现在可以使用自然语言描述测试流程了，AI会基于页面结构生成准确的选择器。
            </Text>
            <div style={{ marginTop: 24 }}>
              <Button type="primary" onClick={onCancel}>
                完成
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Modal
      title="管理页面结构"
      visible={visible}
      onCancel={onCancel}
      width={800}
      footer={currentStep === 3 ? null : (
        <Button onClick={onCancel}>取消</Button>
      )}
      destroyOnClose
    >
      <Steps
        current={currentStep}
        items={steps}
        style={{ marginBottom: 24 }}
      />
      
      {renderStepContent()}
    </Modal>
  );
};

export default PageStructureEditor;