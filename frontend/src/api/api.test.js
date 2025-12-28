import apiClient from '../api/axios';
import { projectsAPI } from '../api/projects';
import axios from 'axios';

jest.mock('axios');

describe('API 客户端', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('projectsAPI.getAll 成功获取项目列表', async () => {
    const mockProjects = [
      { id: 1, name: '项目1' },
      { id: 2, name: '项目2' },
    ];

    apiClient.get = jest.fn().mockResolvedValue({ data: mockProjects });

    const response = await projectsAPI.getAll();
    expect(apiClient.get).toHaveBeenCalledWith('/projects/');
    expect(response.data).toEqual(mockProjects);
  });

  test('projectsAPI.create 创建项目', async () => {
    const newProject = { name: '新项目', description: '测试项目' };
    apiClient.post = jest.fn().mockResolvedValue({ data: { id: 1, ...newProject } });

    const response = await projectsAPI.create(newProject);
    expect(apiClient.post).toHaveBeenCalledWith('/projects/', newProject);
    expect(response.data.name).toBe('新项目');
  });
});
