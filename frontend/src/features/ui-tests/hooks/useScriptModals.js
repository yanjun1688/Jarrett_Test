/**
 * 脚本Modal状态管理Hook
 */
import { useReducer } from 'react';

const initialState = {
  executionModalVisible: false,
  executionDetail: null,
  createModalVisible: false,
  editModalVisible: false,
  editingScript: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SHOW_EXECUTION':
      return {
        ...state,
        executionModalVisible: true,
        executionDetail: action.payload,
      };
    case 'HIDE_EXECUTION':
      return { ...state, executionModalVisible: false, executionDetail: null };
    case 'SHOW_CREATE':
      return { ...state, createModalVisible: true };
    case 'HIDE_CREATE':
      return { ...state, createModalVisible: false };
    case 'SHOW_EDIT':
      return { ...state, editModalVisible: true, editingScript: action.payload };
    case 'HIDE_EDIT':
      return { ...state, editModalVisible: false, editingScript: null };
    default:
      return state;
  }
}

/**
 * 脚本Modal状态管理Hook
 */
function useScriptModals() {
  const [state, dispatch] = useReducer(reducer, initialState);

  return {
    ...state,
    dispatch,
  };
}

export default useScriptModals;
