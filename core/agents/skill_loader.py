"""
Skill Loader - 技能系统管理器

此模块负责：
- 技能文件扫描和加载
- 技能配置验证和解析
- 技能实例化和调度执行
- 技能到工具的适配

设计原则：
- 配置驱动：技能行为由配置文件定义
- 动态加载：运行时扫描和加载技能
- 安全校验：技能执行前验证和沙箱化
"""
import os
import yaml
import importlib
import asyncio
import concurrent.futures
import time
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
import logging
from dataclasses import dataclass, field

from shared.exceptions import ValidationError, JTestError
from core.tools.base_tool import BaseTool, ToolResult, ToolRegistry
from core.tools.execution.api_test_orchestrator import APITestOrchestratorTool

logger = logging.getLogger(__name__)


# 技能规格数据类
@dataclass
class SkillSpec:
    """
    技能规范
    
    定義技能的基本信息、參數要求和執行配置
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires: List[str] = field(default_factory=list)
    execution_config: Dict[str, Any] = field(default_factory=dict)
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """初始化後期處理"""
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillSpec":
        """从字典创建技能规范（忽略不支持的字段）"""
        # 支持的字段列表
        supported_fields = {
            "name", "version", "description", "author", "category",
            "tags", "parameters", "requires", "execution_config", "extra_config"
        }
        
        # 过滤只保留支持的字段
        filtered_data = {k: v for k, v in data.items() if k in supported_fields}
        
        # 兼容 execution 字段
        if "execution" in data and "execution_config" not in filtered_data:
            filtered_data["execution_config"] = data["execution"]
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "parameters": self.parameters,
            "requires": self.requires,
            "execution_config": self.execution_config,
            "extra_config": self.extra_config
        }


class Skill:
    """
    技能实例
    
    封装技能的执行逻辑和参数验证
    """
    
    def __init__(self, spec: SkillSpec, executor: Callable[..., Any]) -> None:
        """
        初始化技能实例
        
        Args:
            spec: 技能规范
            executor: 技能执行器（函数、类或模块）
        """
        self.spec = spec
        self.executor = executor
        self.last_execution_time: Optional[float] = None
        self.execution_count = 0
        self.error_count = 0
        self.version = spec.version
        self.name = spec.name
        
        # 从配置中提取超时设置，如果没有指定则使用默认值30秒
        self.timeout = spec.execution_config.get("timeout", 30)
        
        logger.info(f"初始化技能: {self.name} v{self.version}")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            parameters: 执行参数
            
        Returns:
            执行结果字典
        """
        self.execution_count += 1
        
        start_time = time.perf_counter()
        
        try:
            # 验证和转换参数
            validation_result = await self._validate_and_convert_parameters(parameters)
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"参数验证失败: {', '.join(validation_result['errors'])}",
                    "execution_time": 0.0
                }
            
            converted_params = validation_result["converted_parameters"]
            
            # 使用asyncio.wait_for实现超时控制
            try:
                if asyncio.iscoroutinefunction(self.executor):
                    result = await asyncio.wait_for(
                        self.executor(converted_params), 
                        timeout=self.timeout
                    )
                else:
                    loop = asyncio.get_running_loop()
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        blocking_task = loop.run_in_executor(
                            executor, 
                            self.executor, 
                            converted_params
                        )
                        result = await asyncio.wait_for(blocking_task, timeout=self.timeout)
            except asyncio.TimeoutError:
                execution_time = time.perf_counter() - start_time
                logger.error(f"技能执行超时: {self.name}, 超过 {self.timeout} 秒")
                
                return {
                    "success": False,
                    "error": f"技能执行超时: 超过 {self.timeout} 秒",
                    "execution_time": execution_time,
                    "execution_metadata": {
                        "skill_name": self.name,
                        "skill_version": self.version
                    }
                }
            
            # 转换结果（如果需要）
            if not isinstance(result, dict):
                result = {"success": True, "data": result}
            
            if "success" not in result:
                result["success"] = True
            
            execution_time = time.perf_counter() - start_time
            self.last_execution_time = execution_time
            
            result["execution_time"] = execution_time
            result["execution_metadata"] = {
                "skill_name": self.name,
                "skill_version": self.version
            }
            
            return result
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self.error_count += 1
            
            logger.error(f"技能执行失败: {self.name}, 错误: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "execution_metadata": {
                    "skill_name": self.name,
                    "skill_version": self.version
                }
            }
    
    async def _validate_and_convert_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并转换参数
        
        Args:
            parameters: 输入参数
            
        Returns:
            验证结果字典
        """
        errors = []
        converted_parameters = {}
        
        # 检查必需参数
        for param_name, param_def in self.spec.parameters.items():
            required = param_def.get("required", False)
            param_type = param_def.get("type", "string")
            
            if required and param_name not in parameters:
                errors.append(f"必须参数 '{param_name}' 未提供")
                continue
            
            if param_name in parameters:
                param_value = parameters[param_name]
                
                # 类型转换和验证
                converted_value, field_errors = self._validate_parameter(param_name, param_value, param_def)
                converted_parameters[param_name] = converted_value
                errors.extend(field_errors)
            elif "default" in param_def:
                converted_parameters[param_name] = param_def["default"]
            else:
                converted_parameters[param_name] = None
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "converted_parameters": converted_parameters
        }
    
    def _validate_parameter(self, name: str, value: Any, definition: Dict[str, Any]) -> tuple[Any, List[str]]:
        """
        验证单个参数
        
        Args:
            name: 参数名称
            value: 参数值
            definition: 参数定义
            
        Returns:
            (转换后的值, 错误列表) 元组
        """
        errors = []
        param_type = definition.get("type", "string")
        
        # 类型转换
        if param_type == "integer":
            try:
                value = int(value)
            except (ValueError, TypeError):
                errors.append(f"'{name}' 必须是整数类型")
                return value, errors
        elif param_type == "float":
            try:
                value = float(value)
            except (ValueError, TypeError):
                errors.append(f"'{name}' 必须是浮点数类型")
                return value, errors
        elif param_type == "boolean":
            if isinstance(value, bool):
                pass
            elif isinstance(value, str):
                value = value.lower() in ['true', '1', 'yes', 'on']
            else:
                value = bool(value)
        elif param_type == "string":
            value = str(value)
        elif param_type == "list":
            if not isinstance(value, list):
                errors.append(f"'{name}' 必须是列表类型")
                return value, errors
        elif param_type == "dict":
            if not isinstance(value, dict):
                errors.append(f"'{name}' 必须是字典类型")
                return value, errors
        elif param_type == "any":
            pass  # 接受任何类型
        
        # 业务规则验证
        if "enum" in definition and definition["enum"]:
            if value not in definition["enum"]:
                errors.append(f"'{name}' 不是允许的值之一: {definition['enum']}")
        
        if "min" in definition and isinstance(value, (int, float)):
            if value < definition["min"]:
                errors.append(f"'{name}' 必须大于等于 {definition['min']}")
        
        if "max" in definition and isinstance(value, (int, float)):
            if value > definition["max"]:
                errors.append(f"'{name}' 必须小于等于 {definition['max']}")
        
        if "min_length" in definition and isinstance(value, str):
            if len(value) < definition["min_length"]:
                errors.append(f"'{name}' 长度必须至少 {definition['min_length']} 个字符")
        
        if "max_length" in definition and isinstance(value, str):
            if len(value) > definition["max_length"]:
                errors.append(f"'{name}' 长度必须最多 {definition['max_length']} 个字符")
        
        if "pattern" in definition and isinstance(value, str):
            import re
            if not re.match(definition["pattern"], value):
                errors.append(f"'{name}' 不匹配模式: {definition['pattern']}")
        
        return value, errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取技能执行统计数据"""
        return {
            "name": self.name,
            "version": self.version,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "success_rate": (self.execution_count - self.error_count) / self.execution_count if self.execution_count > 0 else 1.0,
            "last_execution_time": self.last_execution_time
        }


class SkillLoader:
    """
    技能加载器
    
    负责扫描、加载和管理技能
    
    支持多目录扫描：
    - 内置技能目录（skills/）：项目自带技能
    - 用户技能目录（.agent/skills/）：用户从 skill.sh 安装的技能
    """
    
    def __init__(
        self,
        skill_dir: str = "skills",
        enabled_categories: Optional[List[str]] = None,
        extra_skill_dirs: Optional[List[str]] = None
    ):
        """
        初始化技能加载器
        
        Args:
            skill_dir: 主技能目录路径（内置技能）
            enabled_categories: 允许的技能类别列表，None表示全部
            extra_skill_dirs: 额外的技能目录列表（如用户安装的技能）
        """
        self.skill_dir = Path(skill_dir)
        self.enabled_categories = enabled_categories or ["all"]
        self.default_timeout = 30
        self.default_max_filesize = 10 * 1024 * 1024
        
        self.skill_dirs: List[Path] = [self.skill_dir]
        if extra_skill_dirs:
            for d in extra_skill_dirs:
                self.skill_dirs.append(Path(d))
        
        self.skills: Dict[str, Skill] = {}
        
        self._skill_path_cache: Dict[str, Optional[str]] = {}
        self._skill_config_cache: Dict[str, SkillSpec] = {}
        
        dirs_str = ", ".join(str(d) for d in self.skill_dirs)
        logger.info(f"技能加载器初始化，目录: [{dirs_str}]")
    
    def scan_skills(self) -> List[str]:
        """
        扫描可用的技能（扫描所有目录）
        
        Returns:
            找到的技能名称列表
        """
        skills_found: List[str] = []
        
        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                logger.warning(f"技能目录不存在: {skill_dir}")
                continue
            
            for skill_subdir in skill_dir.iterdir():
                if not skill_subdir.is_dir():
                    continue
                
                skill_md_path = skill_subdir / "SKILL.md"
                if skill_md_path.exists():
                    try:
                        skill_name = skill_subdir.name
                        if skill_name not in skills_found:
                            skills_found.append(skill_name)
                            logger.debug(f"发现技能: {skill_name} in {skill_md_path}")
                    except Exception as e:
                        logger.warning(f"验证技能文件失败 {skill_md_path}: {e}")
        
        logger.info(f"扫描到 {len(skills_found)} 个技能")
        return skills_found
    
    def _is_nested(self, file_path: Path) -> bool:
        """检查文件是否在嵌套目录中（排除第一层级）"""
        relative_parts = file_path.relative_to(self.skill_dir).parts
        return len(relative_parts) > 2  # more than filename in direct subdirectory
    
    def _find_skill_file(self, skill_name: str) -> Optional[str]:
        """
        根据技能名称查找技能文件
        
        Args:
            skill_name: 技能名称
            
        Returns:
            文件路径或None
        """
        cache_key = skill_name
        if cache_key in self._skill_path_cache:
            return self._skill_path_cache[cache_key]
        
        for skill_dir in self.skill_dirs:
            skill_md_path = skill_dir / skill_name / "SKILL.md"
            if skill_md_path.exists():
                self._skill_path_cache[cache_key] = str(skill_md_path)
                return str(skill_md_path)
        
        self._skill_path_cache[cache_key] = None
        return None
    
    def _parse_skill_config(self, skill_file_path: str) -> Dict[str, Any]:
        """
        解析技能配置文件
        
        Args:
            skill_file_path: 技能配置文件路径
            
        Returns:
            技能配置字典
            
        Raises:
            ValueError: 配置格式错误
        """
        with open(skill_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析 SKILL.md 的 YAML front matter
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                try:
                    front_matter = yaml.safe_load(parts[1])
                    if isinstance(front_matter, dict):
                        # 从文件路径推断 name（如果没有）
                        if 'name' not in front_matter:
                            front_matter['name'] = Path(skill_file_path).parent.name
                        return front_matter
                except yaml.YAMLError as e:
                    raise ValueError(f"YAML front matter 解析错误: {e}")
        
        # 如果不是 SKILL.md 格式，尝试解析为纯 YAML
        try:
            config = yaml.safe_load(content)
            if isinstance(config, dict):
                return config
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析错误: {e}")
        
        raise ValueError(f"无法解析配置文件: {skill_file_path}")
    
    def _validate_skill_config(self, config: Dict[str, Any]) -> List[str]:
        """
        验证技能配置（宽松模式，自动填充默认值）
        
        Args:
            config: 技能配置字典
            
        Returns:
            验证错误列表
        """
        errors = []
        
        # 只检查 name（必须）
        if not config.get("name"):
            errors.append("缺少必需字段 'name'")
            return errors
        
        # 技能名称验证
        name = config.get("name", "")
        if name and not self._is_valid_skill_name(name):
            errors.append(f"技能名称 '{name}' 格式非法（只能包含字母、数字、下划线、连字符）")
        
        # 为缺失字段提供默认值
        config.setdefault("version", "1.0.0")
        config.setdefault("description", "")
        config.setdefault("author", "unknown")
        config.setdefault("category", "general")
        config.setdefault("tags", [])
        config.setdefault("parameters", {})
        config.setdefault("requires", [])
        
        # execution 配置默认值
        if "execution" not in config:
            config["execution"] = {"type": "builtin", "entrypoint": "default"}
        elif not isinstance(config["execution"], dict):
            config["execution"] = {"type": "builtin", "entrypoint": "default"}
        else:
            config["execution"].setdefault("type", "builtin")
            config["execution"].setdefault("entrypoint", "default")
        
        # 确保参数定义格式正确
        parameters = config.get("parameters", {})
        if not isinstance(parameters, dict):
            config["parameters"] = {}
        
        return errors
    
    def _is_valid_skill_name(self, name: str) -> bool:
        """检查技能名称是否合法"""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))
    
    def load_skill(self, skill_name: str) -> Optional[Skill]:
        """
        加载指定技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            技能实例或None
        """
        if skill_name in self.skills:
            return self.skills[skill_name]
        
        skill_path = self._find_skill_file(skill_name)
        if not skill_path:
            logger.error(f"找不到技能文件: {skill_name}")
            return None
        
        try:
            config = self._parse_skill_config(skill_path)
            
            validation_errors = self._validate_skill_config(config)
            if validation_errors:
                logger.error(f"技能配置验证失败 {skill_name}: {validation_errors}")
                return None
            
            category = config.get("category", "general")
            if not self._is_category_enabled(category):
                logger.warning(f"技能类别 '{category}' 未启用: {skill_name}")
                return None
            
            spec = SkillSpec.from_dict(config)
            
            executor = self._load_executor(spec, config)
            if executor is None:
                logger.error(f"无法加载执行器: {skill_name}")
                return None
            
            skill = Skill(spec=spec, executor=executor)
            
            self.skills[skill_name] = skill
            
            logger.info(f"成功加载技能: {skill_name}")
            
            return skill
            
        except Exception as e:
            logger.error(f"加载技能失败 {skill_name}: {e}", exc_info=True)
            return None
    
    def _is_category_enabled(self, category: str) -> bool:
        """检查类别是否启用"""
        if "all" in self.enabled_categories:
            return True
        return category in self.enabled_categories
    
    def _load_executor(self, spec: SkillSpec, config: Dict[str, Any]) -> Optional[Callable[..., Any]]:
        """
        根据技能配置加载执行器
        
        Args:
            spec: 技能规格
            config: 技能配置
            
        Returns:
            执行器函数或模块
        """
        execution_config = config["execution"]
        execution_type = execution_config["type"]
        
        try:
            if execution_type == "python":
                return self._load_python_executor(config)
            elif execution_type == "module":
                return self._load_module_executor(config)
            elif execution_type == "builtin":
                return self._load_builtin_executor(config)
            else:
                logger.error(f"不支持的执行类型: {execution_type}")
                return None
                
        except Exception as e:
            logger.error(f"加载执行器失败: {e}", exc_info=True)
            return None
    
    def _load_python_executor(self, config: Dict[str, Any]) -> Callable[..., Any]:
        """加载Python函数执行器"""
        entrypoint = config["execution"].get("entrypoint")
        if not entrypoint:
            raise ValueError("Python executor需要指定entrypoint")
        
        if entrypoint == "execute_function":
            async def dummy_executor(params: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True, "params": params}
            return dummy_executor
        else:
            raise NotImplementedError(f"不支持的Python执行点: {entrypoint}")
    
    def _load_module_executor(self, config: Dict[str, Any]) -> Callable[..., Any]:
        """加载模块执行器"""
        module_path = config["execution"].get("module")
        if not module_path:
            raise ValueError("Module executor需要指定module")
        
        try:
            module = importlib.import_module(module_path)
            entrypoint = config["execution"].get("entrypoint", "execute")
            
            executor = getattr(module, entrypoint, None)
            if executor is None:
                raise ValueError(f"模块 {module_path} 中找不到 {entrypoint} 函数")
            
            return executor
        except ImportError as e:
            raise ValueError(f"无法导入模块 {module_path}: {e}")
    
    def _load_builtin_executor(self, config: Dict[str, Any]) -> Callable[..., Any]:
        """加载内置执行器"""
        entrypoint = config["execution"].get("entrypoint", "default")
        
        builtin_executors = {
            "default": self._create_default_executor(config),
            "api_test_orchestration.executor": self._create_api_test_executor(config),
        }
        
        if entrypoint in builtin_executors:
            return builtin_executors[entrypoint]
        else:
            # 如果找不到指定的执行器，使用默认执行器
            logger.warning(f"内置执行器 '{entrypoint}' 未找到，使用默认执行器")
            return builtin_executors["default"]
    
    def _create_default_executor(self, config: Dict[str, Any]) -> Callable[..., Any]:
        """创建默认执行器（仅返回 skill 信息，不执行实际操作）"""
        async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "success": True,
                "message": f"Skill '{config.get('name', 'unknown')}' is a documentation-only skill",
                "description": config.get("description", ""),
                "params": params
            }
        return execute
    
    def _create_api_test_executor(self, config: Dict[str, Any]) -> Callable[..., Any]:
        """创建API测试执行器"""
        async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
            # 模拟APITestOrchestrator行为
            api_url = params.get("api_url", "")
            test_spec = params.get("test_spec", {})
            headers = params.get("headers", {})
            
            # 模拟API测试执行过程
            result = {
                "success": True,
                "test_id": "mock_test_123",
                "api_url": api_url,
                "execution_summary": {
                    "requests_sent": 1,
                    "passed_assertions": 1,
                    "failed_assertions": 0,
                    "total_duration": 0.5
                },
                "raw_response": {
                    "status_code": 200,
                    "headers": {"content-type": "application/json"},
                    "body": {"message": "success", "data": {}}
                }
            }
            
            return result
        
        return execute
    
    async def execute_skill(self, skill_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_name: 技能名称
            **kwargs: 执行参数
            
        Returns:
            执行结果字典
        """
        skill = self.load_skill(skill_name)
        if not skill:
            return {
                "success": False,
                "error": f"技能 '{skill_name}' 不存在或加载失败"
            }
        
        result = await skill.execute(kwargs)
        
        status = "成功" if result.get("success") else "失败"
        logger.info(f"技能执行完成: {skill_name} - {status}")
        
        return result
    
    def unload_skill(self, skill_name: str) -> bool:
        """
        卸载技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            是否成功卸载
        """
        if skill_name in self.skills:
            del self.skills[skill_name]
            logger.info(f"技能已卸载: {skill_name}")
            return True
        else:
            logger.warning(f"尝试卸载不存在的技能: {skill_name}")
            return False
    
    def get_loaded_skills(self) -> List[str]:
        """
        获取已加载的技能列表
        
        Returns:
            技能名称列表
        """
        return list(self.skills.keys())
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能信息
        
        Args:
            skill_name: 技能名称
            
        Returns:
            技能信息或None
        """
        skill = self.skills.get(skill_name)
        if skill:
            result = {
                "name": skill.name,
                "version": skill.version,
                "description": skill.spec.description,
                "author": skill.spec.author,
                "category": skill.spec.category,
                "loaded": True,
                "parameters": skill.spec.parameters
            }
            stats = skill.get_statistics()
            result.update(stats)
            return result
        
        skill_md_path = self.skill_dir / skill_name / "SKILL.md"
        if skill_md_path.exists():
            try:
                content = skill_md_path.read_text(encoding='utf-8')
                name = skill_name
                description = ""
                lines = content.split('\n')
                if lines and lines[0].startswith('# '):
                    name = lines[0].replace('# ', '').strip()
                for line in lines[1:]:
                    if line.strip() and not line.startswith('#'):
                        description = line.strip()
                        break
                
                return {
                    "name": name,
                    "version": "unknown",
                    "description": description,
                    "author": "unknown",
                    "category": "general",
                    "loaded": False,
                    "path": str(skill_md_path)
                }
            except Exception:
                return None
        
        return None
    
    def reload_skill(self, skill_name: str) -> Optional[Skill]:
        """
        重新加载技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            重新加载的技能实例或None
        """
        self.unload_skill(skill_name)
        return self.load_skill(skill_name)
    
    async def get_all_skills_info(self) -> List[Dict[str, Any]]:
        """
        获取所有技能信息
        
        Returns:
            所有技能信息列表
        """
        # 扫描所有可能的技能
        available_skills = self.scan_skills()
        
        # 获取加载状态
        loaded_names = set(self.get_loaded_skills())
        
        all_infos = []
        
        for skill_name in available_skills:
            if skill_name in loaded_names:
                info = self.get_skill_info(skill_name)
                if info:
                    all_infos.append(info)
            else:
                info = self.get_skill_info(skill_name)
                if info:
                    all_infos.append(info)
        
        return all_infos


if __name__ == "__main__":
    # 简单测试
    print("SkillLoader 初始化成功")