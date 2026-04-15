"""
Actions转换器 - 将步骤数据转换为统一的actions JSON格式
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StepsToActionsConverter:
    """将步骤数据转换为actions格式"""
    
    @staticmethod
    def convert(steps: List[Any]) -> List[Dict[str, Any]]:
        """
        转换步骤数据列表为actions格式
        
        Args:
            steps: 步骤数据列表（字典格式或模型对象格式）
            
        Returns:
            List[Dict]: actions列表
        """
        actions: List[Dict[str, Any]] = []
        
        for idx, step in enumerate(steps, start=1):
            action_type: Any = None
            action_params: Dict[str, Any] = {}
            description: str = ''
            element_locator: Any = None
            is_enabled: bool = True
            
            if hasattr(step, 'action_type'):
                action_type = step.action_type
                action_params = step.action_params or {}
                description = step.description or ''
                element_locator = step.element_locator
                is_enabled = getattr(step, 'is_enabled', True)
            elif isinstance(step, dict):
                action_type = step.get('action_type')
                action_params = step.get('action_params', {})
                description = step.get('description', '')
                element_locator = step.get('element_locator')
                is_enabled = step.get('is_enabled', True)
            else:
                logger.warning(f"不支持的step格式: {type(step)}")
                continue
            
            if not is_enabled:
                continue
            
            action = {
                'id': f'action_{idx}',
                'order': idx,
                'type': action_type,
                'params': action_params.copy(),
                'description': description
            }
            
            if element_locator:
                if hasattr(element_locator, 'locator_type'):
                    action['selector'] = {
                        'type': element_locator.locator_type,
                        'value': element_locator.locator_value
                    }
                elif isinstance(element_locator, dict):
                    action['selector'] = {
                        'type': element_locator.get('locator_type'),
                        'value': element_locator.get('locator_value')
                    }
            
            if action_type == 'navigate' and 'url' in action_params:
                if 'selector' in action:
                    del action['selector']
            
            actions.append(action)
        
        return actions
    
    @staticmethod
    def convert_from_recording(steps: List[Any]) -> List[Dict[str, Any]]:
        """
        转换录制步骤为actions格式（专用于录制场景）
        
        录制步骤格式：
        {
            "action_type": "navigate/click/fill/...",
            "action_params": {"url": "...", "value": "..."},
            "element_locator": {"locator_type": "id/css/...", "locator_value": "..."},
            "description": "..."
        }
        
        Actions格式：
        {
            "id": "action_1",
            "order": 1,
            "type": "navigate/click/fill/...",
            "params": {"url": "...", "value": "..."},
            "selector": {"type": "id/css/...", "value": "..."},
            "description": "..."
        }
        
        Args:
            steps: 录制步骤列表
            
        Returns:
            List[Dict]: actions列表
        """
        actions: List[Dict[str, Any]] = []
        
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                logger.warning(f"跳过非字典格式的step: {type(step)}")
                continue
            
            action_type = step.get('action_type')
            if not action_type:
                logger.warning(f"跳过缺少action_type的step: {step}")
                continue
            
            action_params = step.get('action_params', {})
            description = step.get('description', '')
            element_locator = step.get('element_locator')
            
            action = {
                'id': f'action_{idx}',
                'order': idx,
                'type': action_type,
                'params': action_params.copy() if isinstance(action_params, dict) else {},
                'description': description
            }
            
            if element_locator and isinstance(element_locator, dict):
                locator_type = element_locator.get('locator_type')
                locator_value = element_locator.get('locator_value')
                
                if locator_type and locator_value:
                    action['selector'] = {
                        'type': locator_type,
                        'value': locator_value
                    }
            
            if action_type == 'navigate' and 'url' in action_params:
                if 'selector' in action:
                    del action['selector']
            
            actions.append(action)
            logger.debug(f"转换录制步骤 {idx}: {action_type} -> action_{idx}")
        
        logger.info(f"成功转换 {len(actions)} 个录制步骤为actions格式")
        return actions


def convert_to_actions(source_data: Any, source_type: str) -> List[Dict[str, Any]]:
    """
    统一的转换接口（支持steps和actions转换）
    
    Args:
        source_data: 源数据（steps列表或actions列表）
        source_type: 源类型（支持'steps'和'actions'）
        
    Returns:
        List[Dict]: actions列表（统一格式）
        
    Raises:
        ValueError: 不支持的source_type
    """
    if source_type == 'steps':
        converter = StepsToActionsConverter()
        return converter.convert(source_data)
    elif source_type == 'actions':
        converter = StepsToActionsConverter()
        return converter.convert_from_recording(source_data)
    else:
        raise ValueError(f"不支持的source_type: {source_type}，仅支持: 'steps', 'actions'")