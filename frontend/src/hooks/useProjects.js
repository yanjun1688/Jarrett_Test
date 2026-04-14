/**
 * useProjects Hook
 * 获取项目列表
 */
import { useState, useEffect, useCallback } from 'react';
import { projectsAPI } from '../api/projects';

export const useProjects = () => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await projectsAPI.getAll();
      setProjects(response.data.results || response.data || []);
    } catch (err) {
      setError(err.response?.data?.error || '获取项目列表失败');
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    loading,
    error,
    refetch: fetchProjects,
  };
};

export default useProjects;