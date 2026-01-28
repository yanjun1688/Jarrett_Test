import axios from 'axios';
import { message } from 'antd';
import logger from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token刷新标志，防止并发刷新
let isRefreshing = false;
let refreshSubscribers = [];

// 订阅刷新完成事件
const subscribeTokenRefresh = (cb) => {
  refreshSubscribers.push(cb);
};

// 通知所有订阅者
const onTokenRefreshed = (token) => {
  refreshSubscribers.map(cb => cb(token));
  refreshSubscribers = [];
};

// 刷新token的函数
const refreshToken = async () => {
  if (isRefreshing) {
    // 如果正在刷新，等待刷新完成
    return new Promise((resolve) => {
      subscribeTokenRefresh((token) => {
        resolve(token);
      });
    });
  }

  isRefreshing = true;
  const currentToken = localStorage.getItem('authToken');

  try {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh-token/`, {}, {
      headers: {
        'Authorization': `Token ${currentToken}`
      }
    });

    const { token, expires_at } = response.data;
    localStorage.setItem('authToken', token);
    if (expires_at) {
      localStorage.setItem('tokenExpiresAt', expires_at);
    }

    onTokenRefreshed(token);
    isRefreshing = false;
    return token;
  } catch (error) {
    isRefreshing = false;
    // 刷新失败，清除认证信息并跳转登录
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    localStorage.removeItem('tokenExpiresAt');
    window.location.href = '/login';
    throw error;
  }
};

// 检查token是否即将过期（提前1小时刷新）
const shouldRefreshToken = () => {
  const expiresAt = localStorage.getItem('tokenExpiresAt');
  if (!expiresAt) return false;

  const expiresTime = new Date(expiresAt).getTime();
  const now = new Date().getTime();
  const oneHour = 60 * 60 * 1000; // 1小时

  // 如果距离过期时间小于1小时，需要刷新
  return (expiresTime - now) < oneHour;
};

// 请求拦截器
apiClient.interceptors.request.use(
  async (config) => {
    // 检查token是否即将过期，如果是则自动刷新
    if (shouldRefreshToken()) {
      try {
        const newToken = await refreshToken();
        config.headers.Authorization = `Token ${newToken}`;
      } catch (error) {
        // 刷新失败，请求会被401拦截器处理
        logger.error('Token refresh failed:', error);
      }
    } else {
      // 正常添加token
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Token ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    if (error.response) {
      const status = error.response.status;
      
      // 处理403权限错误 - 显示友好提示，让用户点击按钮跳转到登录页
      if (status === 403) {
        // 清除本地存储的认证信息
        localStorage.removeItem('authToken');
        localStorage.removeItem('userInfo');
        localStorage.removeItem('tokenExpiresAt');
        
        // 显示友好的错误提示，带确认按钮
        message.error({
          content: '您没有访问权限，请重新登录',
          duration: 0, // 不自动关闭
          onClose: () => {
            window.location.href = '/login';
          }
        });
        
        // 如果用户点击了提示，跳转到登录页
        // 同时提供一个延迟自动跳转（5秒后）
        setTimeout(() => {
          window.location.href = '/login';
        }, 5000);
        
        return Promise.reject(error);
      }
      
      // 处理401未授权错误 - 尝试刷新token
      if (status === 401) {
        const originalRequest = error.config;
        
        // 如果是刷新token的请求失败，直接跳转登录
        if (originalRequest.url.includes('/auth/refresh-token/')) {
          localStorage.removeItem('authToken');
          localStorage.removeItem('userInfo');
          localStorage.removeItem('tokenExpiresAt');
          message.error('登录已过期，请重新登录', 3);
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
          return Promise.reject(error);
        }
        
        // 尝试刷新token
        try {
          const newToken = await refreshToken();
          // 使用新token重试原请求
          originalRequest.headers.Authorization = `Token ${newToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // 刷新失败，清除认证信息并跳转登录
          localStorage.removeItem('authToken');
          localStorage.removeItem('userInfo');
          localStorage.removeItem('tokenExpiresAt');
          message.error('登录已过期，请重新登录', 3);
          setTimeout(() => {
            window.location.href = '/login';
          }, 2000);
          return Promise.reject(refreshError);
        }
      }
      
      // 其他服务器响应错误
      logger.error('API Error:', status, error.response.data);
    } else if (error.request) {
      // 请求已发出但没有收到响应
      logger.error('Network Error:', error.request);
    } else {
      // 发送请求时出错
      logger.error('Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
