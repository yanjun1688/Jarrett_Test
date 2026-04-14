/**
 * 脚本相关工具函数
 */
import { ACTION_TYPES, getColorHex } from '../../../constants';

/**
 * 把表单里的步骤数据转成后端需要的actions格式
 * @param {Array} formSteps - 表单步骤数据
 * @returns {Array} 后端需要的actions数据结构
 */
export function buildStepsPayload(formSteps) {
  console.log('[scriptUtils] buildStepsPayload 接收:', { count: formSteps?.length, sample: formSteps?.[0] });
  
  const actions = formSteps.map((step, index) => {
    const action = {
      id: `action_${index + 1}`,
      order: index + 1,
      type: step.action_type,
      description: step.description || '',
    };

    // 元素定位（转换为selector格式）
    if (step.locator_type && step.locator_value) {
      action.selector = {
        type: step.locator_type,
        value: step.locator_value,
      };
    }

    // 操作参数
    const params = {};
    switch (step.action_type) {
      case ACTION_TYPES.NAVIGATE:
        params.url = step.url || '';
        break;
      case ACTION_TYPES.FILL:
        if (step.value) params.value = step.value;
        break;
      case ACTION_TYPES.SELECT:
        if (step.value) params.value = step.value;
        break;
      // click不需要额外参数
      default:
        break;
    }
    
    if (Object.keys(params).length > 0) {
      action.params = params;
    }

    console.log(`[scriptUtils] 生成action ${index}:`, action);
    return action;
  });
  
  console.log('[scriptUtils] buildStepsPayload 完成:', actions);
  return actions;
}

/**
 * 从后端actions数据转换为表单格式
 * @param {Array} actions - 后端actions数据（统一格式）
 * @returns {Array} 表单步骤数据
 */
export function convertStepsToFormFormat(actions) {
  console.log('[scriptUtils] convertStepsToFormFormat 接收:', { count: actions?.length, sample: actions?.[0] });
  
  return (actions || []).map((action, idx) => {
    const actionType = action.type || action.action_type;
    const formStep = {
      action_type: actionType,
      description: action.description || '',
    };
    
    console.log(`[scriptUtils] 转换步骤 ${idx}:`, { type: actionType, hasSelector: !!action.selector, hasParams: !!action.params });
    
    // 处理selector（新格式）
    if (action.selector) {
      formStep.locator_type = action.selector.type;
      formStep.locator_value = action.selector.value;
    }
    // 向后兼容：处理element_locator（旧格式）
    else if (action.element_locator) {
      formStep.locator_type = action.element_locator.locator_type || action.element_locator.type;
      formStep.locator_value = action.element_locator.locator_value || action.element_locator.value;
    }
    
    // 处理params
    const params = action.params || action.action_params;
    if (params) {
      // 支持的操作类型
      if (actionType === ACTION_TYPES.NAVIGATE || action.action_type === ACTION_TYPES.NAVIGATE) {
        formStep.url = params.url;
      } else if (actionType === ACTION_TYPES.FILL || action.action_type === ACTION_TYPES.FILL) {
        formStep.value = params.value;
      } else if (actionType === ACTION_TYPES.SELECT || action.action_type === ACTION_TYPES.SELECT) {
        formStep.value = params.value;
      }
    }
    
    console.log(`[scriptUtils] 转换后的表单步骤 ${idx}:`, formStep);
    return formStep;
  });
}

// 导出颜色函数（使用常量）
export { getColorHex };
