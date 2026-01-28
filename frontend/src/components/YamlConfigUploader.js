import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api';
import '../css/YamlConfigUploader.css';

// Monaco Editor 支持YAML语法高亮
import Editor from '@monaco-editor/react';
import yaml from 'js-yaml';

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
    <div className="yaml-config-container">
      <div className="yaml-config-header">
        <h1 className="yaml-config-title">YAML配置上传工具</h1>
      </div>

      {/* 成功/错误消息 */}
      {success && <div className="yaml-config-success-message">{success}</div>}
      {error && <div className="yaml-config-danger-message">{error}</div>}

      <div className="yaml-config-card">
        <div className="yaml-config-card-title">基础信息</div>

        <div className="yaml-config-form-group">
          <label className="yaml-config-label">集合名称 *</label>
          <input
            type="text"
            className="yaml-config-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="请输入请求集合名称"
          />
        </div>

        <div className="yaml-config-form-group">
          <label className="yaml-config-label">描述</label>
          <textarea
            className="yaml-config-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="请输入测试集合的描述信息（可选）"
          />
        </div>

        <div className="yaml-config-form-group">
          <label className="yaml-config-label">执行模式</label>
          <select
            className="yaml-config-select"
            value={executionMode}
            onChange={(e) => setExecutionMode(e.target.value)}
          >
            <option value="chain">链式执行（支持变量传递）</option>
            <option value="sequential">顺序执行</option>
            <option value="concurrent">并发执行</option>
          </select>
        </div>
      </div>

      <div className="yaml-config-card">
        <div className="yaml-config-card-title">YAML配置编辑器</div>

        <div className="yaml-config-file-upload">
          <input
            type="file"
            id="yaml-file"
            className="yaml-config-file-input"
            accept=".yaml,.yml"
            onChange={handleFileUpload}
          />
          <label htmlFor="yaml-file" className="yaml-config-upload-button">
            📁 上传YAML文件
          </label>
          <button
            type="button"
            className="yaml-config-secondary-button"
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
        <div className="yaml-config-card">
          <div className="yaml-config-card-title">转换预览</div>

          <div className="yaml-config-preview-summary">
            <div className="yaml-config-preview-item">
              <div className="yaml-config-preview-label">总步骤数</div>
              <div className="yaml-config-preview-value">{preview.total_steps}</div>
            </div>
            <div className="yaml-config-preview-item">
              <div className="yaml-config-preview-label">断言总数</div>
              <div className="yaml-config-preview-value">
                {preview.steps_preview.reduce((sum, s) => sum + s.assertions_count, 0)}
              </div>
            </div>
            <div className="yaml-config-preview-item">
              <div className="yaml-config-preview-label">提取变量</div>
              <div className="yaml-config-preview-value">
                {preview.variables ? preview.variables.extracted.length : 0}
              </div>
            </div>
          </div>

          {/* 变量信息 */}
          {preview.variables && (
            <div className="yaml-config-variables-section">
              <strong>变量信息：</strong><br />
              {preview.variables.defined.length > 0 && (
                <div>
                  定义的环境变量:
                  {preview.variables.defined.map(v =>
                    <span key={v} className="yaml-config-variable-tag">{v}</span>
                  )}
                </div>
              )}
              {preview.variables.extracted.length > 0 && (
                <div style={{ marginTop: '5px' }}>
                  提取的变量:
                  {preview.variables.extracted.map(v =>
                    <span key={v} className="yaml-config-variable-tag yaml-config-variable-tag-extracted">{v}</span>
                  )}
                </div>
              )}
              {preview.variables.undefined && preview.variables.undefined.length > 0 && (
                <div style={{ marginTop: '5px' }}>
                  未定义变量:
                  {preview.variables.undefined.map(v =>
                    <span key={v} className="yaml-config-variable-tag yaml-config-variable-tag-undefined">{v}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 步骤预览 */}
          <div>
            {preview.steps_preview.map((step) => (
              <div key={step.order} className="yaml-config-step-preview">
                <div className="yaml-config-step-header">
                  <span>步骤 {step.order + 1}: {step.name}</span>
                  <span>{step.method} {step.url}</span>
                </div>
                <div className="yaml-config-step-details">
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
      <div className="yaml-config-validation-section">
        <button
          type="button"
          className="yaml-config-secondary-button"
          onClick={handleValidate}
          disabled={loading}
        >
          {loading ? '🔄 验证中...' : '🔍 验证YAML'}
        </button>

        {isValid === false && validationErrors.length > 0 && (
          <div className="yaml-config-error-list">
            <strong>验证错误:</strong>
            {validationErrors.map((err, idx) => (
              <div key={idx} className="yaml-config-error-item">
                • {err.message}
              </div>
            ))}
          </div>
        )}

        {validationWarnings.length > 0 && (
          <div className="yaml-config-warning-list">
            <strong>验证警告:</strong>
            {validationWarnings.map((warn, idx) => (
              <div key={idx} className="yaml-config-warning-item">
                • {warn.message}
              </div>
            ))}
          </div>
        )}

        {isValid === true && (
          <div className="yaml-config-success-message" style={{ marginTop: '10px' }}>
            ✓ YAML配置验证通过，可以保存
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="yaml-config-action-buttons">
        <button
          type="button"
          className="yaml-config-secondary-button"
          onClick={() => window.history.back()}
        >
          取消
        </button>
        <button
          type="button"
          className="yaml-config-primary-button"
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
