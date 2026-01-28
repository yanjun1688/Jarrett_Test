/**
 * UI测试脚本管理Hook
 */
import { useReducer, useCallback, useEffect } from 'react';
import { notification } from 'antd';
import { uiTestsAPI, projectsAPI } from '../../../api';
import { handleApiError } from '../../../utils/errorHandler';

const initialState = {
  loading: true,
  scripts: [],
  projects: [],
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_SCRIPTS':
      return { ...state, scripts: action.payload, loading: false };
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    default:
      return state;
  }
}

/**
 * UI测试脚本管理Hook
 */
function useUiTestScripts() {
  const [state, dispatch] = useReducer(reducer, initialState);

  // 加载脚本列表
  const loadScripts = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const res = await uiTestsAPI.getScripts();
      dispatch({
        type: 'SET_SCRIPTS',
        payload: res.data.results || res.data,
      });
    } catch (err) {
      handleApiError(err, '获取 UI 测试脚本失败');
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  // 加载项目列表
  const loadProjects = useCallback(async () => {
    try {
      const res = await projectsAPI.getAll();
      dispatch({
        type: 'SET_PROJECTS',
        payload: res.data.results || res.data,
      });
    } catch (err) {
      handleApiError(err, '获取项目列表失败');
    }
  }, []);

  useEffect(() => {
    loadScripts();
    loadProjects();
  }, [loadScripts, loadProjects]);

  return {
    ...state,
    loadScripts,
    loadProjects,
  };
}

export default useUiTestScripts;
