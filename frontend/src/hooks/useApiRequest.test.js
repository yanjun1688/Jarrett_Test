import { renderHook, act } from '@testing-library/react';
import useApiRequest from './useApiRequest';

const mockApiFunction = jest.fn();

describe('useApiRequest', () => {
  beforeEach(() => {
    mockApiFunction.mockReset();
    mockApiFunction.mockResolvedValue({ data: { id: 1, name: '测试数据' } });
  });

  test('初始状态', () => {
    const { result } = renderHook(() => useApiRequest(mockApiFunction));

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  test('成功执行请求', async () => {
    const { result } = renderHook(() => useApiRequest(mockApiFunction));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual({ id: 1, name: '测试数据' });
    expect(result.current.error).toBeNull();
  });
});
