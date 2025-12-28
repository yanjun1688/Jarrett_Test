import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Upload,
  message,
  Row,
  Col,
  Tag,
  Divider,
  Typography,
  Alert
} from 'antd';
import { UploadOutlined, CheckCircleOutlined, ExclamationCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { requestCollectionsAPI } from '../api';

const { Title, Text } = Typography;
const { TextArea } = Input;

// YAML示例模板
const YAML_TEMPLATE = `# API配置示例
name: "用户登录流程测试"
description: "完整的用户登录和业务测试流程"

# 环境变量定义
env_vars:
  base_url: "https://api.example.com"
  username: "test_user"
  password: "test_pass123"

# 测试步骤
steps:
  # 步骤1: 获取Token
  - name: "获取访问令牌"
    description: "通过用户名密码获取访问令牌"

    # 请求配置
    request:
      url: "{{base_url}}/api/v1/auth/login"
      method: "POST"
      headers:
        Content-Type: "application/json"
      body:
        username: "{{username}}"
        password: "{{password}}"

    # 变量提取
    extract:
      - name: "access_token"
        path: "$.data.token"
      - name: "user_id"
        path: "$.data.user.id"

    # 断言配置
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
      - type: "jsonpath"
        path: "$.code"
        expected: "0"
        comparison: "equals"

  # 步骤2: 使用Token访问用户信息API
  - name: "获取用户信息"
    description: "使用Token获取用户详细信息"

    request:
      url: "{{base_url}}/api/v1/user/info"
      method: "GET"
      headers:
        Authorization: "Bearer {{access_token}}"
        Content-Type: "application/json"

    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
      - type: "jsonpath"
        path: "$.code"
        expected: "0"
        comparison: "equals"
      - type: "jsonpath"
        path: "$.data.id"
        expected: "{{user_id}}"
        comparison: "equals"

execution:
  mode: "chain"  # 执行模式: chain(链式)/sequential(顺序)/concurrent(并发)
  continue_on_failure: false
`;

function YamlConfigUploaderSimple() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const [yamlContent, setYamlContent] = useState(YAML_TEMPLATE);
  const [preview, setPreview] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [isValid, setIsValid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 文件上传处理
  const handleFileUpload = (info) => {
    const file = info.file;
    const reader = new FileReader();
    reader.onload = (e) => {
      setYamlContent(e.target.result);
      message.success('文件上传成功');
    };
    reader.readAsText(file);
    return false; // 阻止自动上传
  };

  // 加载示例
  const loadExample = () => {
    setYamlContent(YAML_TEMPLATE);
    message.info('已加载示例配置');
  };

  // 验证YAML
  const handleValidate = async () => {
    setLoading(true);
    setValidationErrors([]);
    setValidationWarnings([]);

    try {
      // Base64编码
      const base64Content = btoa(yamlContent);

      const response = await requestCollectionsAPI.validateYaml(projectId, {
        yaml_content: base64Content,
        check_variables: true,
        check_jsonpath: true,
      });

      if (response.data.code === 200) {
        setIsValid(true);
        setValidationErrors([]);
        setValidationWarnings(response.data.data.issues || []);
        setPreview(response.data.data);
        message.success('✓ YAML验证通过！');
      } else {
        setIsValid(false);
        setValidationErrors(response.data.data.errors || []);
        setValidationWarnings(response.data.data.warnings || []);
        message.error('✗ YAML验证失败');
      }
    } catch (err) {
      setIsValid(false);
      message.error('验证请求失败: ' + (err.response?.data?.message || err.message));
      setValidationErrors([{
        level: 'error',
        message: err.response?.data?.message || err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  // 保存（转换）
  const handleSave = async (values) => {
    setSaving(true);

    try {
      // Base64编码
      const base64Content = btoa(yamlContent);

      const response = await requestCollectionsAPI.yamlToCollection(projectId, {
        name: values.name,
        description: values.description || '',
        yaml_content: base64Content,
        execution_mode: values.execution_mode || 'chain',
        validate_only: false,
      });

      if ([200, 201].includes(response.data.code)) {
        message.success('✓ 保存成功！Collection ID: ' + response.data.data.collection_id);

        // 2秒后跳转到集合列表
        setTimeout(() => {
          navigate('/request-collections');
        }, 2000);
      } else {
        message.error('保存失败: ' + response.data.message);
      }
    } catch (err) {
      if (err.response?.status === 422) {
        // 验证错误
        setValidationErrors(err.response.data.errors || [])
        setValidationWarnings(err.response.data.warnings || [])
        message.error('✗ YAML格式错误或验证失败');
      } else {
        message.error('保存请求失败: ' + (err.response?.data?.message || err.message));
      }
    } finally {
      setSaving(false);
    }
  };

  // 自动预览 - 简化版，不解析YAML，直接显示基本信息
  useEffect(() => {
    if (yamlContent.trim()) {
      // 统计基本信息
      const stepMatches = yamlContent.match(/^\s*-\s+name:/gm);
      const totalSteps = stepMatches ? stepMatches.length : 0;

      if (totalSteps > 0) {
        setPreview({
          total_steps: totalSteps,
          steps_preview: Array.from({ length: totalSteps }, (_, idx) => ({
            order: idx,
            name: `步骤 ${idx + 1}`,
            method: '',
            url: '',
            assertions_count: 0,
            extract_vars: [],
          })),
          variables: {
            defined: [],
            extracted: [],
          },
        });
      }
    } else {
      setPreview(null);
    }
  }, [yamlContent]);

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <Title level={2} style={{ marginBottom: '20px' }}>YAML配置上传工具</Title>

      {isValid && (
        <Alert
          message="✓ YAML验证通过！可以保存到数据库"
          type="success"
          showIcon
          style={{ marginBottom: '20px' }}
        />
      )}

      {isValid === false && validationErrors.length > 0 && (
        <Alert
          message="✗ YAML验证失败，请修正错误后再试"
          type="error"
          showIcon
          style={{ marginBottom: '20px' }}
        />
      )}

      <Row gutter={20}>
        {/* 左侧配置区域 */}
        <Col span={12}>
          <Card title="基础信息" style={{ marginBottom: '20px' }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
              initialValues={{
                execution_mode: 'chain',
              }}
            >
              <Form.Item
                label="集合名称"
                name="name"
                rules={[{ required: true, message: '请输入集合名称' }]}
              >
                <Input placeholder="请输入请求集合名称" />
              </Form.Item>

              <Form.Item label="描述" name="description">
                <TextArea rows={3} placeholder="请输入测试集合的描述信息（可选）" />
              </Form.Item>

              <Form.Item label="执行模式" name="execution_mode">
                <Select>
                  <Select.Option value="chain">链式执行（支持变量传递）</Select.Option>
                  <Select.Option value="sequential">顺序执行</Select.Option>
                  <Select.Option value="concurrent">并发执行</Select.Option>
                </Select>
              </Form.Item>
            </Form>
          </Card>

          <Card
            title="YAML配置编辑器"
            extra={
              <Space>
                <Button
                  icon={<UploadOutlined />}
                  onClick={loadExample}
                  size="small"
                >
                  加载示例
                </Button>
              </Space>
            }
          >
            <Form.Item>
              <Upload
                beforeUpload={handleFileUpload}
                accept=".yaml,.yml"
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />} style={{ marginBottom: '10px' }}>
                  上传YAML文件
                </Button>
              </Upload>
            </Form.Item>

            <TextArea
              rows={25}
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              style={{
                fontFamily: 'monospace',
                fontSize: '14px',
              }}
              placeholder="请输入或粘贴YAML配置内容"
            />
          </Card>
        </Col>

        {/* 右侧预览区域 */}
        <Col span={12}>
          {preview && (
            <Card title="转换预览" style={{ marginBottom: '20px' }}>
              <Row gutter={16} style={{ marginBottom: '20px' }}>
                <Col span={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Text type="secondary">总步骤数</Text>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                      {preview.total_steps}
                    </div>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Text type="secondary">断言总数</Text>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                      {preview.steps_preview.reduce((sum, s) => sum + s.assertions_count, 0)}
                    </div>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Text type="secondary">提取变量</Text>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#faad14' }}>
                      {preview.variables ? preview.variables.extracted.length : 0}
                    </div>
                  </Card>
                </Col>
              </Row>

              {/* 变量信息 */}
              {preview.variables && (
                <div style={{ marginBottom: '20px' }}>
                  {preview.variables.defined.length > 0 && (
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: '8px' }}>定义的环境变量:</Text>
                      {preview.variables.defined.map(v => (
                        <Tag key={v} color="blue" style={{ marginBottom: '5px' }}>{v}</Tag>
                      ))}
                    </div>
                  )}
                  {preview.variables.extracted.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <Text strong style={{ display: 'block', marginBottom: '8px' }}>提取的变量:</Text>
                      {preview.variables.extracted.map(v => (
                        <Tag key={v} color="green" style={{ marginBottom: '5px' }}>{v}</Tag>
                      ))}
                    </div>
                  )}
                  {preview.variables.undefined && preview.variables.undefined.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <Text strong style={{ display: 'block', marginBottom: '8px' }}>未定义变量:</Text>
                      {preview.variables.undefined.map(v => (
                        <Tag key={v} color="orange" style={{ marginBottom: '5px' }}>{v}</Tag>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <Divider>步骤预览</Divider>

              <div>
                {preview.steps_preview.map((step) => (
                  <Card
                    key={step.order}
                    size="small"
                    style={{ marginBottom: '10px', borderLeft: '4px solid #1890ff' }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                      步骤 {step.order + 1}: {step.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {step.method} {step.url}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                      断言数: {step.assertions_count}
                      {step.extract_vars.length > 0 && (
                        <span> | 提取变量: {step.extract_vars.join(', ')}</span>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </Card>
          )}

          {/* 验证结果 */}
          <Card title="验证结果">
            <Space style={{ marginBottom: '20px' }}>
              <Button
                type="primary"
                icon={loading ? <LoadingOutlined /> : <CheckCircleOutlined />}
                onClick={handleValidate}
                loading={loading}
              >
                验证YAML
              </Button>
              <Button
                type="default"
                onClick={() => {
                  setValidationErrors([]);
                  setValidationWarnings([]);
                  setIsValid(null);
                  setPreview(null);
                }}
              >
                清空结果
              </Button>
            </Space>

            {validationErrors.length > 0 && (
              <Alert
                message="验证错误"
                description={
                  <div>
                    {validationErrors.map((err, idx) => (
                      <div key={idx} style={{ marginBottom: '5px' }}>
                        • {err.message}
                      </div>
                    ))}
                  </div>
                }
                type="error"
                showIcon
                style={{ marginTop: '10px' }}
              />
            )}

            {validationWarnings.length > 0 && (
              <Alert
                message="验证警告"
                description={
                  <div>
                    {validationWarnings.map((warn, idx) => (
                      <div key={idx} style={{ marginBottom: '5px' }}>
                        • {warn.message}
                      </div>
                    ))}
                  </div>
                }
                type="warning"
                showIcon
                style={{ marginTop: '10px' }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <div style={{ textAlign: 'center', marginTop: '30px' }}>
        <Space size="large">
          <Button
            size="large"
            onClick={() => navigate('/request-collections')}
          >
            取消
          </Button>
          <Button
            type="primary"
            size="large"
            onClick={() => form.submit()}
            disabled={saving || isValid === false || loading}
            loading={saving}
          >
            保存并创建集合
          </Button>
        </Space>
      </div>
    </div>
  );
}

export default YamlConfigUploaderSimple;
