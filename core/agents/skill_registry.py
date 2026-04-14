"""
Skill Registry - 技能注册表

此模块提供全局的技能注册和管理功能，支持：
- 技能注册和注销
- 技能查找和检索
- 全局访问点
"""
from typing import Dict, Optional, List
from threading import Lock
from core.agents.skill_loader import Skill


class SkillRegistry:
    """
    技能注册表
    
    线程安全的技能注册和管理类
    """
    
    def __init__(self):
        """初始化技能注册表"""
        self._skills: Dict[str, 'Skill'] = {}
        self._lock = Lock()
        
    def register_skill(self, skill: 'Skill') -> bool:
        """
        注册技能
        
        Args:
            skill: 要注册的技能实例
            
        Returns:
            True 如果注册成功，False 如果技能已存在
        """
        with self._lock:
            if skill.name in self._skills:
                return False
            self._skills[skill.name] = skill
            return True
            
    def get_skill(self, name: str) -> Optional['Skill']:
        """
        获取技能
        
        Args:
            name: 技能名称
            
        Returns:
            技能实例或None（如果不存在）
        """
        with self._lock:
            return self._skills.get(name)
            
    def get_all_skills(self) -> List['Skill']:
        """
        获取所有技能
        
        Returns:
            技能实例列表
        """
        with self._lock:
            return list(self._skills.values())
            
    def unregister_skill(self, name: str) -> bool:
        """
        注销技能
        
        Args:
            name: 技能名称
            
        Returns:
            True 如果注销成功，False 如果技能不存在
        """
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                return True
            return False
            
    def get_skills_count(self) -> int:
        """
        获取技能数量
        
        Returns:
            当前注册的技能数量
        """
        with self._lock:
            return len(self._skills)
    
    def get_skill_names(self) -> List[str]:
        """
        获取所有已注册技能的名称列表
        
        Returns:
            技能名称列表
        """
        with self._lock:
            return list(self._skills.keys())
            
    def clear(self) -> None:
        """清空所有技能"""
        with self._lock:
            self._skills.clear()


# 全局技能注册表实例
global_skill_registry = SkillRegistry()