import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { createUseStyles } from 'react-jss';
import api from '../api';

// Monaco Editor 支持YAML语法高亮
import Editor from '@monaco-editor/react';
import yaml from 'js-yaml';

const useStyles = createUseStyles({
  container: {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    paddingBottom: '10px',
    borderBottom: '2px solid #eee',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
  },
  card: {
    background: '#fff',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  cardTitle: {
    fontSize: '18px',
    fontWeight: 'bold',
    marginBottom: '15px',
    color: '#333',
  },
  formGroup: {
    marginBottom: '15px',
  },
  label: {
    display: 'block',
    marginBottom: '5px',
    fontWeight: '600',
    color: '#333',
  },
  input: {
    width: '100%',
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    '&:focus': {
      outline: 'none',
      borderColor: '#1890ff',
    },
  },
  textarea: {
    width: '100%',
    minHeight: '80px',
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    fontFamily: 'monospace',
    '&:focus': {
      outline: 'none',
      borderColor: '#1890ff',
    },
  },
  select: {
    width: '100%',
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    background: '#fff',
    '&:focus': {
      outline: 'none',
      borderColor: '#1890ff',
    },
  },
  editorContainer: {
    height: '500px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  fileUpload: {
    marginBottom: '15px',
  },
  fileInput: {
    display: 'none',
  },
  uploadButton: {
    padding: '10px 20px',
    background: '#1890ff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    '&:hover': {
      background: '#40a9ff',
    },
  },
  previewSection: {
    background: '#f5f5f5',
    borderRadius: '4px',
    padding: '15px',
    marginBottom: '15px',
  },
  previewSummary: {
    display: 'flex',
    gap: '20px',
    marginBottom: '15px',
  },
  previewItem: {
    flex: 1,
    textAlign: 'center',
    padding: '10px',
    background: '#fff',
    borderRadius: '4px',
  },
  previewLabel: {
    fontSize: '12px',
    color: '#666',
    marginBottom: '5px',
  },
  previewValue: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#1890ff',
  },
  stepPreview: {
    background: '#fff',
    borderRadius: '4px',
    padding: '10px',
    marginBottom: '10px',
    borderLeft: '4px solid #1890ff',
  },
  stepHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontWeight: 'bold',
    marginBottom: '5px',
  },
  stepDetails: {
    fontSize: '12px',
    color: '#666',
  },
  validationSection: {
    marginTop: '15px',
  },
  errorList: {
    background: '#fff2f0',
    border: '1px solid #ffccc7',
    borderRadius: '4px',
    padding: '10px',
    marginTop: '10px',
  },
  warningList: {
    background: '#fffbe6',
    border: '1px solid #ffe58f',
    borderRadius: '4px',
    padding: '10px',
    marginTop: '10px',
  },
  errorItem: {
    color: '#f5222d',
    fontSize: '13px',
    marginBottom: '5px',
  },
  warningItem: {
    color: '#faad14',
    fontSize: '13px',
    marginBottom: '5px',
  },
  actionButtons: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'center',
    marginTop: '20px',
  },
  primaryButton: {
    padding: '10px 30px',
    background: '#1890ff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    '&:hover': {
      background: '#40a9ff',
    },
    '&:disabled': {
      background: '#d9d9d9',
      cursor: 'not-allowed',
    },
  },
  secondaryButton: {
    padding: '10px 30px',
    background: '#fff',
    color: '#1890ff',
    border: '1px solid #1890ff',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    '&:hover': {
      background: '#e6f7ff',
    },
  },
  successMessage: {
    background: '#f6ffed',
    border: '1px solid #b7eb8f',
    borderRadius: '4px',
    padding: '15px',
    marginBottom: '15px',
    color: '#52c41a',
  },
  dangerMessage: {
    background: '#fff2f0',
    border: '1px solid #ffccc7',
    borderRadius: '4px',
    padding: '15px',
    marginBottom: '15px',
    color: '#f5222d',
  },
  yamlTextarea: {
    width: '100%',
    minHeight: '500px',
    padding: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '14px',
    '&:focus': {
      outline: 'none',
      borderColor: '#1890ff',
    },
  },
  variablesSection: {
    background: '#e6f7ff',
    border: '1px solid #91d5ff',
    borderRadius: '4px',
    padding: '10px',
    marginBottom: '10px',
  },
  variableTag: {
    display: 'inline-block',
    background: '#1890ff',
    color: '#fff',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    marginRight: '5px',
    marginBottom: '5px',
  },
  variableTagExtracted: {
    background: '#52c41a',
  },
  variableTagUndefined: {
    background: '#faad14',
  },
});

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

function YamlConfigUploader() {
  const classes = useStyles();
  const { projectId } = useParams();

  // 表单状态
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [executionMode, setExecutionMode] = useState('chain');
  const [yamlContent, setYamlContent] = useState(YAML_TEMPLATE);

  // 预览和状态
  const [preview, setPreview] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [isValid, setIsValid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  // 文件上传处理
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      setYamlContent(e.target.result);
    };
    reader.readAsText(file);
  };

  // 加载示例
  const loadExample = () => {
    setYamlContent(YAML_TEMPLATE);
  };

  // 验证YAML
  const handleValidate = async () => {
    setLoading(true);
    setSuccess(null);
    setError(null);

    try {
      // Base64编码
      const base64Content = btoa(yamlContent);

      const response = await api.post(`/projects/${projectId}/yaml/validate/`, {
        yaml_content: base64Content,
        check_variables: true,
        check_jsonpath: true,
      });

      if (response.data.code === 200) {
        setIsValid(true);
        setValidationErrors([]);
        setValidationWarnings(response.data.data.issues || []);
        setPreview(response.data.data);
        setSuccess('✓ YAML验证通过！');
      } else {
        setIsValid(false);
        setValidationErrors(response.data.data.errors || []);
        setValidationWarnings(response.data.data.warnings || []);
        setError('✗ YAML验证失败');
      }
    } catch (err) {
      setIsValid(false);
      setError('验证请求失败: ' + (err.response?.data?.message || err.message));
      setValidationErrors([{
        level: 'error',
        message: err.response?.data?.message || err.message
      }]);
    } finally {
      setLoading(false);
    }
  };

  // 保存（转换）
  const handleSave = async () => {
    setSaving(true);
    setSuccess(null);
    setError(null);

    try {
      // Base64编码
      const base64Content = btoa(yamlContent);

      const response = await api.post(`/projects/${projectId}/yaml-to-collection/`, {
        name,
        description,
        yaml_content: base64Content,
        execution_mode: executionMode,
        validate_only: false,
      });

      if ([200, 201].includes(response.data.code)) {
        setSuccess('✓ 保存成功！Collection ID: ' + response.data.data.collection_id);

        // 可以跳转到集合详情页或执行页
        // setTimeout(() => {
        //   window.location.href = `/collections/${response.data.data.collection_id}/execute`;
        // }, 2000);
      } else {
        setError('保存失败: ' + response.data.message);
      }
    } catch (err) {
      if (err.response?.status === 422) {
        // 验证错误
        setValidationErrors(err.response.data.errors || [])
        setValidationWarnings(err.response.data.warnings || [])
        setError('✗ YAML格式错误或验证失败');
      } else {
        setError('保存请求失败: ' + (err.response?.data?.message || err.message));
      }
    } finally {
      setSaving(false);
    }
  };

  // 自动预览（防抖）
  useEffect(() => {
    const timer = setTimeout(() => {
      if (yamlContent.trim()) {
        // 基础预览（不需要后端验证）
        try {
          const config = yaml.load(yamlContent);
          if (config && config.steps) {
            const steps_preview = config.steps.map((step, idx) => ({
              order: idx,
              name: step.name || `步骤${idx + 1}`,
              method: step.request?.method || '',
              url: step.request?.url || '',
              assertions_count: step.assertions ? step.assertions.length : 0,
              extract_vars: step.extract ? step.extract.map(e => e.name) : [],
            }));

            setPreview({
              total_steps: config.steps.length,
              steps_preview,
              variables: {
                defined: config.env_vars ? Object.keys(config.env_vars) : [],
                extracted: [],
              },
            });
          }
        } catch (e) {
          // YAML解析失败，不显示预览
          setPreview(null);
        }
      } else {
        setPreview(null);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [yamlContent]);

  return (
    <div className={classes.container}>
      <div className={classes.header}>
        <h1 className={classes.title}>YAML配置上传工具</h1>
      </div>

      {/* 成功/错误消息 */}
      {success && <div className={classes.successMessage}>{success}</div>}
      {error && <div className={classes.dangerMessage}>{error}</div>}

      <div className={classes.card}>
        <div className={classes.cardTitle}>基础信息</div>

        <div className={classes.formGroup}>
          <label className={classes.label}>集合名称 *</label>
          <input
            type="text"
            className={classes.input}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="请输入请求集合名称"
          />
        </div>

        <div className={classes.formGroup}>
          <label className={classes.label}>描述</label>
          <textarea
            className={classes.textarea}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="请输入测试集合的描述信息（可选）"
          />
        </div>

        <div className={classes.formGroup}>
          <label className={classes.label}>执行模式</label>
          <select
            className={classes.select}
            value={executionMode}
            onChange={(e) => setExecutionMode(e.target.value)}
          >
            <option value="chain">链式执行（支持变量传递）</option>
            <option value="sequential">顺序执行</option>
            <option value="concurrent">并发执行</option>
          </select>
        </div>
      </div>

      <div className={classes.card}>
        <div className={classes.cardTitle}>YAML配置编辑器</div>

        <div className={classes.fileUpload}>
          <input
            type="file"
            id="yaml-file"
            className={classes.fileInput}
            accept=".yaml,.yml"
            onChange={handleFileUpload}
          />
          <label htmlFor="yaml-file" className={classes.uploadButton}>
            📁 上传YAML文件
          </label>
          <button
            type="button"
            className={classes.secondaryButton}
            onClick={loadExample}
            style={{ marginLeft: '10px' }}
          >
            📋 加载示例
          </button>
        </div>

        <Editor
          height="500px"
          language="yaml"
          theme="vs-light"
          value={yamlContent}
          onChange={(value) => setYamlContent(value || '')}
          options={{
            fontSize: 14,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>

      {/* 预览区域 */}
      {preview && (
        <div className={classes.card}>
          <div className={classes.cardTitle}>转换预览</div>

          <div className={classes.previewSummary}>
            <div className={classes.previewItem}>
              <div className={classes.previewLabel}>总步骤数</div>
              <div className={classes.previewValue}>{preview.total_steps}</div>
            </div>
            <div className={classes.previewItem}>
              <div className={classes.previewLabel}>断言总数</div>
              <div className={classes.previewValue}>
                {preview.steps_preview.reduce((sum, s) => sum + s.assertions_count, 0)}
              </div>
            </div>
            <div className={classes.previewItem}>
              <div className={classes.previewLabel}>提取变量</div>
              <div className={classes.previewValue}>
                {preview.variables ? preview.variables.extracted.length : 0}
              </div>
            </div>
          </div>

          {/* 变量信息 */}
          {preview.variables && (
            <div className={classes.variablesSection}>
              <strong>变量信息：</strong><br />
              {preview.variables.defined.length > 0 && (
                <div>
                  定义的环境变量:
                  {preview.variables.defined.map(v =>
                    <span key={v} className={classes.variableTag}>{v}</span>
                  )}
                </div>
              )}
              {preview.variables.extracted.length > 0 && (
                <div style={{ marginTop: '5px' }}>
                  提取的变量:
                  {preview.variables.extracted.map(v =>
                    <span key={v} className={`${classes.variableTag} ${classes.variableTagExtracted}`}>{v}</span>
                  )}
                </div>
              )}
              {preview.variables.undefined && preview.variables.undefined.length > 0 && (
                <div style={{ marginTop: '5px' }}>
                  未定义变量:
                  {preview.variables.undefined.map(v =>
                    <span key={v} className={`${classes.variableTag} ${classes.variableTagUndefined}`}>{v}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 步骤预览 */}
          <div>
            {preview.steps_preview.map((step) => (
              <div key={step.order} className={classes.stepPreview}>
                <div className={classes.stepHeader}>
                  <span>步骤 {step.order + 1}: {step.name}</span>
                  <span>{step.method} {step.url}</span>
                </div>
                <div className={classes.stepDetails}>
                  断言数: {step.assertions_count}
                  {step.extract_vars.length > 0 && (
                    <span> | 提取变量: {step.extract_vars.join(', ')}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 验证结果 */}
      <div className={classes.validationSection}>
        <button
          type="button"
          className={classes.secondaryButton}
          onClick={handleValidate}
          disabled={loading}
        >
          {loading ? '🔄 验证中...' : '🔍 验证YAML'}
        </button>

        {isValid === false && validationErrors.length > 0 && (
          <div className={classes.errorList}>
            <strong>验证错误:</strong>
            {validationErrors.map((err, idx) => (
              <div key={idx} className={classes.errorItem}>
                • {err.message}
              </div>
            ))}
          </div>
        )}

        {validationWarnings.length > 0 && (
          <div className={classes.warningList}>
            <strong>验证警告:</strong>
            {validationWarnings.map((warn, idx) => (
              <div key={idx} className={classes.warningItem}>
                • {warn.message}
              </div>
            ))}
          </div>
        )}

        {isValid === true && (
          <div className={classes.successMessage} style={{ marginTop: '10px' }}>
            ✓ YAML配置验证通过，可以保存
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className={classes.actionButtons}>
        <button
          type="button"
          className={classes.secondaryButton}
          onClick={() => window.history.back()}
        >
          取消
        </button>
        <button
          type="button"
          className={classes.primaryButton}
          onClick={handleSave}
          disabled={saving || !name || !yamlContent}
        >
          {saving ? '💾 保存中...' : '💾 保存并创建集合'}
        </button>
      </div>
    </div>
  );
}

export default YamlConfigUploader;
