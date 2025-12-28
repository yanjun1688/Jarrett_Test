import { useAuth } from '../context/AuthContext';

/**
 * 权限检查 Hook
 * @returns {Object} 权限对象和相关方法
 */
export const usePermissions = () => {
  const { permissions } = useAuth();

  /**
   * 检查是否有 CRUD 权限
   * @returns {boolean} 是否有 CRUD 权限
   */
  const hasCrudPermission = () => {
    return permissions?.crud || false;
  };

  /**
   * 检查是否有查看权限
   * @returns {boolean} 是否有查看权限
   */
  const hasViewPermission = () => {
    // 只要有登录就有查看权限
    return true;
  };

  return {
    permissions,
    hasCrudPermission,
    hasViewPermission,
    canEdit: hasCrudPermission(),
    canDelete: hasCrudPermission(),
    canCreate: hasCrudPermission(),
    canExecute: hasCrudPermission(),
  };
};

export default usePermissions;