import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import axios from '../api/axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState({ crud: false });

  // 计算用户权限
  // 设计理念：admin用户自动拥有所有权限，其他用户通过角色控制
  const calculatePermissions = useCallback((userData) => {
    if (!userData) {
      return { crud: false };
    }

    // admin用户自动拥有所有权限
    if (userData.username === 'admin') {
      return { crud: true };
    }

    // 检查是否有 crud 权限的角色
    if (userData.roles && Array.isArray(userData.roles)) {
      const hasCrudPermission = userData.roles.some(role =>
        role.permission_type === 'crud' || role.permission === 'crud'
      );

      return {
        crud: hasCrudPermission
      };
    }

    return { crud: false };
  }, []);

  // 检查本地存储中的认证信息
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const userInfo = localStorage.getItem('userInfo');

    if (token && userInfo) {
      try {
        const parsedUser = JSON.parse(userInfo);
        setUser(parsedUser);
        setPermissions(calculatePermissions(parsedUser));
      } catch (error) {
        console.error('Failed to parse user info:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userInfo');
      }
    }
    setLoading(false);
  }, [calculatePermissions]);

  // 登录
  const login = async (username, password) => {
    try {
      const response = await axios.post('/auth/login/', {
        username,
        password,
      });

      const { token, user } = response.data;

      // 存储token和用户信息
      localStorage.setItem('authToken', token);
      localStorage.setItem('userInfo', JSON.stringify(user));
      
      // 存储token过期时间
      if (user.token_expires_at) {
        localStorage.setItem('tokenExpiresAt', user.token_expires_at);
      } else {
        // 如果没有返回过期时间，设置默认7天后过期
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + 7);
        localStorage.setItem('tokenExpiresAt', expiresAt.toISOString());
      }

      setUser(user);
      setPermissions(calculatePermissions(user));

      return { success: true };
    } catch (error) {
      let message = '登录失败';

      if (error.response) {
        if (error.response.status === 401) {
          message = '用户名或密码错误';
        } else if (error.response.status === 400) {
          message = '请输入用户名和密码';
        } else {
          message = error.response.data?.detail || message;
        }
      }

      return { success: false, message };
    }
  };

  // 登出
  const logout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    setUser(null);
  };

  const value = {
    user,
    loading,
    login,
    logout,
    permissions,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
