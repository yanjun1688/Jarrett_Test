import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import loginAxios from '../api/loginAxios';
import logger from '../utils/logger';

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
        logger.error('Failed to parse user info:', error);
        localStorage.removeItem('authToken');
        localStorage.removeItem('userInfo');
      }
    }
    setLoading(false);
  }, [calculatePermissions]);

  // 登录
  const login = async (username, password) => {
    logger.log('[AuthContext] 登录请求:', { username, password: '***' });
    try {
      const startTime = Date.now();
      
      const response = await loginAxios.post('/auth/login/', {
        username,
        password,
      });

      const duration = Date.now() - startTime;
      logger.log('[AuthContext] 登录响应:', { 
        status: response.status, 
        dataKeys: Object.keys(response.data),
        responseData: response.data,
        duration: `${duration}ms`
      });

      if (response.data && response.data.token && response.data.user) {
        const { token, user } = response.data;

        // 存储token和用户信息
        localStorage.setItem('authToken', token);
        localStorage.setItem('userInfo', JSON.stringify(user));
        
        // 存储token过期时间
        if (user.token_expires_at) {
          localStorage.setItem('tokenExpiresAt', user.token_expires_at);
          logger.log('[AuthContext] Token过期时间已存储:', user.token_expires_at);
        } else {
          // 如果没有返回过期时间，设置默认7天后过期
          const expiresAt = new Date();
          expiresAt.setDate(expiresAt.getDate() + 7);
          localStorage.setItem('tokenExpiresAt', expiresAt.toISOString());
          logger.log('[AuthContext] Token过期时间设置为7天后:', expiresAt.toISOString());
        }

        setUser(user);
        setPermissions(calculatePermissions(user));

        logger.log('[AuthContext] 用户登录成功:', {
          username: user.username,
          userId: user.user_id,
          tokenLength: token.length,
          hasUserInfoKey: localStorage.getItem('userInfo') ? true : false
        });

        return { success: true, message: '登录成功' };
      } else {
        logger.error('[AuthContext] 登录响应数据格式错误:', response.data);
        return { success: false, message: '服务器响应数据格式错误' };
      }
    } catch (error) {
      logger.error('[AuthContext] 登录错误详情:', {
        message: error.message,
        status: error.response ? error.response.status : null,
        statusText: error.response ? error.response.statusText : null,
        response: error.response ? error.response.data : null,
        config: error.config ? {
          url: error.config.url,
          method: error.config.method,
          baseURL: error.config.baseURL
        } : null
      });

      let message = '登录失败';

      if (error.response) {
        if (error.response.status === 401) {
          message = '用户名或密码错误';
        } else if (error.response.status === 400) {
          message = '请输入用户名和密码';
        } else if (error.response.data && error.response.data.detail) {
          message = error.response.data.detail;
        } else if (error.response.data && error.response.data.error) {
          message = error.response.data.error;
        } else if (error.response.data && typeof error.response.data === 'string') {
          message = error.response.data;
        } else {
          const errorKeys = Object.keys(error.response.data || {});
          logger.warn('[AuthContext] 未知服务器响应格式:', { 
            keys: errorKeys, 
            data: error.response.data 
          });
          if (errorKeys.includes('username') || errorKeys.includes('password')) {
            const fieldErrors = [];
            if (errorKeys.includes('username')) fieldErrors.push(...error.response.data.username);
            if (errorKeys.includes('password')) fieldErrors.push(...error.response.data.password);
            message = fieldErrors.join(', ') || '用户名或密码输入有误';
          } else {
            message = '登录失败，未知服务器错误';
          }
        }
      } else if (error.request) {
        logger.error('[AuthContext] 请求发送成功但无响应:', error.request);
        message = '无法连接到服务器，请检查网络连接';
      } else {
        logger.error('[AuthContext] 请求配置错误:', error.message);
        message = `请求配置错误: ${error.message}`;
      }

      logger.log('[AuthContext] 登录失败信息:', message);
      return { success: false, message };
    }
  };

  // 登出
  const logout = () => {
    logger.log('[AuthContext] 开始登出...');
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    localStorage.removeItem('tokenExpiresAt');

    logger.log('[AuthContext] 已清除本地存储的认证数据');

    setUser(null);
    setPermissions({ crud: false });

    logger.log('[AuthContext] 用户登出成功, 清理状态完成');
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
