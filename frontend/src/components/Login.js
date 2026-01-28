import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Spin } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import logger from '../utils/logger';
import '../css/Login.css';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    const { username, password } = values;

    const result = await login(username, password);

    if (result.success) {
      message.success('登录成功！');

      // 添加延迟，确保 token 已存储
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 100);
    } else {
      message.error(result.message);
      setLoading(false);
    }
  };

  const onFinishFailed = (errorInfo) => {
  };

  return (
    <div className="login-container">
      <Card className="login-card">
        <div className="login-header">
          <h2>欢迎使用测试平台</h2>
          <p>请登录您的账户</p>
        </div>

        <Form
          name="login"
          className="login-form"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          onFinishFailed={onFinishFailed}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名!' }]}
          >
            <Input
              prefix={<UserOutlined className="site-form-item-icon" />}
              placeholder="用户名"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码!' }]}
          >
            <Input.Password
              prefix={<LockOutlined className="site-form-item-icon" />}
              type="password"
              placeholder="密码"
              disabled={loading}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              className="login-form-button"
              loading={loading}
              disabled={loading}
            >
              登录
            </Button>
          </Form.Item>

          <div className="login-footer">
            <p>还没有账户？请联系管理员</p>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
