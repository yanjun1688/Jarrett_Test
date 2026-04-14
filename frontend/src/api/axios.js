import axios from 'axios';
import { message } from 'antd';
import logger from '../utils/logger';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (cb) => {
  refreshSubscribers.push(cb);
};

const onTokenRefreshed = (token) => {
  refreshSubscribers.map(cb => cb(token));
  refreshSubscribers = [];
};

const refreshToken = async () => {
  if (isRefreshing) {
    return new Promise((resolve) => {
      subscribeTokenRefresh((token) => {
        resolve(token);
      });
    });
  }

  isRefreshing = true;
  const currentToken = localStorage.getItem('authToken');

  logger.log('[Axios] 开始刷新token，当前token:', currentToken ? '***' : null);

  if (!currentToken) {
    isRefreshing = false;
    logger.error('[Axios] 无法刷新token：本地没有有效token');
    throw new Error('No token available');
  }

  try {
    logger.log('[Axios] 发送刷新token请求到 /auth/refresh/');
    const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {}, {
      headers: {
        'Authorization': `Token ${currentToken}`,
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      },
      timeout: 5000 // 添加超时
    });

    logger.log('[Axios] 刷新token响应:', {
      status: response.status,
      dataKeys: Object.keys(response.data || {}),
      hasToken: !!response.data?.token,
      hasExpiresAt: !!response.data?.expires_at
    });

    const { token, expires_at, message } = response.data;
    localStorage.setItem('authToken', token);
    
    if (expires_at) {
      localStorage.setItem('tokenExpiresAt', expires_at);
      logger.log('[Axios] 新的token过期时间已设置:', expires_at);
    }

    logger.log('[Axios] Token刷新成功', message || '');
    onTokenRefreshed(token);
    isRefreshing = false;
    
    return token;
  } catch (error) {
    logger.error('[Axios] Token刷新失败:', {
      message: error.message,
      status: error.response ? error.response.status : null,
      data: error.response ? error.response.data : null,
      config: error.config ? {
        url: error.config.url,
        method: error.config.method,
        baseURL: error.config.baseURL
      } : null
    });
    
    isRefreshing = false;
    localStorage.removeItem('authToken');
    localStorage.removeItem('userInfo');
    localStorage.removeItem('tokenExpiresAt');
    logger.log('[Axios] 已清理本地认证数据');
    throw error;
  }
};

const shouldRefreshToken = () => {
  const expiresAt = localStorage.getItem('tokenExpiresAt');
  if (!expiresAt) return false;

  const expiresTime = new Date(expiresAt).getTime();
  const now = new Date().getTime();
  const oneHour = 60 * 60 * 1000;

  return (expiresTime - now) < oneHour;
};

const redirectToLogin = (msg = '登录已过期，请重新登录') => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('userInfo');
  localStorage.removeItem('tokenExpiresAt');
  message.error(msg, 3);
  setTimeout(() => {
    window.location.href = '/login';
  }, 2000);
};

apiClient.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('authToken');
    
    // 定义不需要认证的白名单路径（忽略查询参数）
    const publicPaths = ['/auth/login/', '/auth/refresh/', '/auth/me/'];
    // 提取路径部分（不包含查询参数和片段）
    const pathOnly = config.url.split(/[?#]/)[0];
    const isPublicPath = publicPaths.some(publicPath => 
      // 检查路径是否以公共路径结尾
      pathOnly.endsWith(publicPath) || 
      // 或者是包含在路径中的子路径（处理完整URL的情况）
      pathOnly.includes(publicPath)
    );
    
    logger.log(`[Axios Request Interceptor] 发送请求:`, {
      url: config.url,
      method: config.method,
      hasAuthHeader: !!config.headers.Authorization,
      tokenExists: !!token,
      isPublicPath: isPublicPath
    });

    // 对于公开路径，直接继续
    if (isPublicPath) {
      return config;
    }

    if (!token) {
      logger.warn('[Axios Request Interceptor] 未找到token，重定向到登录页面');
      redirectToLogin('请先登录');
      return Promise.reject(new Error('No token available'));
    }

    if (shouldRefreshToken()) {
      const expiresAt = localStorage.getItem('tokenExpiresAt');
      logger.log('[Axios Request Interceptor] Token即将过期，需要刷新:', {
        expiresAt,
        now: new Date().toISOString()
      });

      try {
        const newToken = await refreshToken();
        config.headers.Authorization = `Token ${newToken}`;
        logger.log('[Axios Request Interceptor] Token刷新成功，更新头部');
      } catch (error) {
        logger.error('[Axios Request Interceptor] Token刷新失败，重定向到登录页面');
        redirectToLogin('登录已过期，请重新登录');
        return Promise.reject(error);
      }
    } else {
      const expiresAt = localStorage.getItem('tokenExpiresAt');
      const now = new Date().getTime();
      const tokenExpiresAt = new Date(expiresAt).getTime();
      logger.log('[Axios Request Interceptor] Token有效期内，继续请求:', {
        expiresAt,
        now: new Date(now).toISOString(),
        '距离过期还有(min)': Math.round((tokenExpiresAt - now) / 60000)
      });
      
      config.headers.Authorization = `Token ${token}`;
    }

    return config;
  },
  (error) => {
    logger.error('[Axios Request Interceptor] 请求错误:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    logger.log(`[Axios Response Interceptor] 请求成功:`, {
      url: response.config.url,
      method: response.config.method,
      status: response.status,
      statusText: response.statusText,
      duration: response.headers ? 
        (response.headers['request-duration-ms'] || response.headers['x-response-time']) : 
        'unknown'
    });
    return response;
  },
  async (error) => {
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        logger.error('[Axios Response Interceptor] 请求超时:', error.config.url);
        message.error('请求超时，请稍后重试');
      } else {
        logger.error('[Axios Response Interceptor] 网络连接失败:', {
          url: error.config?.url,
          message: error.message,
          code: error.code
        });
        message.error('网络连接失败，请检查网络或后端服务');
      }
      logger.error('Network Error:', error.message);
      return Promise.reject(error);
    }

    const status = error.response.status;
    const originalRequest = error.config;
    
    logger.warn(`[Axios Response Interceptor] API错误 (${status}):`, {
      url: originalRequest.url,
      method: originalRequest.method,
      status: error.response.status,
      statusText: error.response.statusText,
      message: error.message,
      responseKeys: Object.keys(error.response.data || {})
    });

    if (status === 403) {
      const authHeader = originalRequest.headers.Authorization;
      logger.log('[Axios Response Interceptor] 403 权限不足:', {
        url: originalRequest.url,
        hasAuthHeader: !!authHeader,
        tokenValid: !!localStorage.getItem('authToken')
      });
      
      if (!authHeader || !localStorage.getItem('authToken')) {
        redirectToLogin('请重新登录');
      } else {
        redirectToLogin('您没有访问权限');
      }
      return Promise.reject(error);
    }

    if (status === 401) {
      logger.log('[Axios Response Interceptor] 401 未授权:', {
        url: originalRequest.url,
        isRefreshRequest: originalRequest.url.includes('/auth/refresh/'),
        tokenExists: !!localStorage.getItem('authToken')
      });
      
      if (originalRequest.url.includes('/auth/refresh/')) {
        logger.log('[Axios Response Interceptor] 刷新token自身失败，重定向到登录页面');
        redirectToLogin();
        return Promise.reject(error);
      }

      if (!isRefreshing) {
        try {
          logger.log('[Axios Response Interceptor] Token无效，尝试刷新');
          const newToken = await refreshToken();
          originalRequest.headers.Authorization = `Token ${newToken}`;
          logger.log('[Axios Response Interceptor] Token刷新成功，重新发送请求');
          return apiClient(originalRequest);
        } catch (refreshError) {
          logger.error('[Axios Response Interceptor] Token刷新失败，重定向到登录页面:', refreshError);
          redirectToLogin();
          return Promise.reject(refreshError);
        }
      } else {
        logger.log('[Axios Response Interceptor] 另一个刷新token请求正在进行中，等待结果');
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Token ${token}`;
            logger.log('[Axios Response Interceptor] 通过回调获得新的token，继续原请求');
            resolve(apiClient(originalRequest));
          });
        });
      }
    }

    logger.error('API Error details:', {
      url: error.config?.url,
      method: error.config?.method,
      status: status,
      data: error.response.data
    });
    return Promise.reject(error);
  }
);

export default apiClient;
