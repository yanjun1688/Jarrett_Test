"""
YAML 解析器 - 纯解析层，无 Django 依赖

仅负责解析 YAML 内容，不涉及任何数据库操作
"""
import yaml
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class YamlConfig:
    """YAML 配置数据结构"""
    name: str
    description: str
    env_vars: Dict[str, str]
    steps: List[Dict[str, Any]]
    extract_vars: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'env_vars': self.env_vars,
            'steps': self.steps,
            'extract_vars': self.extract_vars
        }


class YamlValidationError(Exception):
    """YAML 验证错误"""
    pass


class YamlParser:
    """
    YAML 解析器
    
    特性：
    - 仅解析 YAML 内容，无任何外部依赖
    - 返回结构化的 YamlConfig 对象
    - 支持验证但不保存
    """
    
    def __init__(self):
        pass
    
    def parse(self, yaml_content: str) -> YamlConfig:
        """
        解析 YAML 内容
        
        Args:
            yaml_content: YAML 字符串内容
            
        Returns:
            YamlConfig: 解析后的配置对象
            
        Raises:
            YamlValidationError: 解析失败时抛出
        """
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise YamlValidationError(f"YAML 解析失败: {e}")
        
        if not isinstance(config, dict):
            raise YamlValidationError("YAML 根节点必须是字典")
        
        return self._parse_config(config)
    
    def _parse_config(self, config: Dict) -> YamlConfig:
        """解析配置字典"""
        name = config.get('name', 'Unnamed Collection')
        description = config.get('description', '')
        env_vars = config.get('env_vars', {})
        steps = config.get('steps', [])
        
        if not steps:
            raise YamlValidationError("缺少 steps 配置")
        
        extract_vars = {}
        for step in steps:
            for extract in step.get('extract', []):
                var_name = extract.get('name')
                if var_name:
                    extract_vars[var_name] = extract.get('from', 'response_body')
        
        return YamlConfig(
            name=name,
            description=description,
            env_vars=env_vars,
            steps=steps,
            extract_vars=extract_vars
        )
    
    def validate(self, yaml_content: str) -> Tuple[bool, List[Dict], List[Dict]]:
        """
        验证 YAML 内容
        
        Args:
            yaml_content: YAML 字符串内容
            
        Returns:
            (is_valid, errors, warnings)
        """
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            errors.append({
                'level': 'error',
                'message': f"YAML 语法错误: {e}",
                'field': 'yaml_syntax'
            })
            return False, errors, warnings
        
        if not isinstance(config, dict):
            errors.append({
                'level': 'error',
                'message': "YAML 根节点必须是字典",
                'field': 'root'
            })
            return False, errors, warnings
        
        if 'name' not in config:
            warnings.append({
                'level': 'warning',
                'message': "未指定 name 字段，将使用默认值",
                'field': 'name'
            })
        
        if 'steps' not in config:
            errors.append({
                'level': 'error',
                'message': "缺少 steps 字段",
                'field': 'steps'
            })
            return False, errors, warnings
        
        steps = config.get('steps', [])
        if not isinstance(steps, list):
            errors.append({
                'level': 'error',
                'message': "steps 必须是数组",
                'field': 'steps'
            })
            return False, errors, warnings
        
        for idx, step in enumerate(steps):
            step_errors, step_warnings = self._validate_step(step, idx)
            errors.extend(step_errors)
            warnings.extend(step_warnings)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_step(self, step: Dict, idx: int) -> Tuple[List[Dict], List[Dict]]:
        """验证单个步骤"""
        errors = []
        warnings = []
        
        required_fields = ['name', 'request']
        for field in required_fields:
            if field not in step:
                errors.append({
                    'level': 'error',
                    'message': f"步骤 {idx + 1} 缺少必填字段: {field}",
                    'field': f'steps[{idx}].{field}'
                })
        
        if 'request' in step:
            request = step['request']
            if not isinstance(request, dict):
                errors.append({
                    'level': 'error',
                    'message': f"步骤 {idx + 1} 的 request 必须是对象",
                    'field': f'steps[{idx}].request'
                })
            elif 'method' not in request:
                warnings.append({
                    'level': 'warning',
                    'message': f"步骤 {idx + 1} 未指定 method，默认使用 GET",
                    'field': f'steps[{idx}].request.method'
                })
            elif request['method'].upper() not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']:
                errors.append({
                    'level': 'error',
                    'message': f"步骤 {idx + 1} 的 method 无效: {request['method']}",
                    'field': f'steps[{idx}].request.method'
                })
        
        if 'assertions' in step:
            assertions = step['assertions']
            if not isinstance(assertions, list):
                errors.append({
                    'level': 'error',
                    'message': f"步骤 {idx + 1} 的 assertions 必须是数组",
                    'field': f'steps[{idx}].assertions'
                })
        
        return errors, warnings
