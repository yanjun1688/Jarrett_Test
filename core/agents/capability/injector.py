from typing import List, Dict, Any, Optional
import logging

from .registry import global_capability_registry
from .cache import CapabilityCache

logger = logging.getLogger(__name__)


class CapabilityInjector:
    """
    能力注入器
    
    将能力清单格式化为数据，提供给 PromptBuilder 使用
    支持：
    - 技能清单数据
    - 工具清单数据
    - MCP 服务器清单数据
    - Token 预算检查（可选使用 TokenCalculator）
    - 缓存优化
    """
    
    MAX_CAPABILITY_TOKENS = 2000
    
    def __init__(self, registry=None, cache=None, token_calc=None):
        self.registry = registry or global_capability_registry
        self.cache = cache or CapabilityCache()
        self.token_calc = token_calc
        
        if self.token_calc is None:
            try:
                from core.context.token_economics import TokenCalculator
                self.token_calc = TokenCalculator()
            except ImportError:
                logger.warning("TokenCalculator not found, using fallback")
    
    def get_skills_data(self) -> List[Dict[str, Any]]:
        """
        获取技能数据
        
        Returns:
            技能数据列表
        """
        logger.info(f"[CapabilityInjector] 获取Skills数据...")
        manifest = self.registry.get_manifest()
        skills_count = len(manifest.skills)
        logger.info(f"[CapabilityInjector] Registry返回 {skills_count}个Skills")
        return [s.to_dict() for s in manifest.skills]
    
    def get_tools_data(self) -> List[Dict[str, Any]]:
        """
        获取工具数据
        
        Returns:
            工具数据列表
        """
        logger.info(f"[CapabilityInjector] 获取Tools数据...")
        manifest = self.registry.get_manifest()
        tools_count = len(manifest.tools)
        logger.info(f"[CapabilityInjector] Registry返回 {tools_count}个Tools")
        return [t.to_dict() for t in manifest.tools]
    
    def get_mcp_servers_data(self) -> List[Dict[str, Any]]:
        """
        获取 MCP 服务器数据
        
        Returns:
            MCP 服务器数据列表
        """
        manifest = self.registry.get_manifest()
        return [m.to_dict() for m in manifest.mcp_servers]
    
    def build_skills_section_text(
        self,
        max_items: Optional[int] = None,
        include_allowed_tools: bool = True
    ) -> str:
        """
        构建技能部分文本
        
        Args:
            max_items: 最大数量限制
            include_allowed_tools: 是否包含 allowed_tools
        
        Returns:
            技能部分的 Markdown 文本
        """
        skills = self.get_skills_data()
        
        if not skills:
            return ""
        
        if max_items:
            skills = skills[:max_items]
        
        lines = ["## 可用技能 (Skills)", ""]
        
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            allowed_tools = skill.get("allowed_tools", [])
            category = skill.get("category", "")
            tags = skill.get("tags", [])
            
            lines.append(f"### {name}")
            lines.append(f"**描述**: {description}")
            
            if include_allowed_tools and allowed_tools:
                lines.append(f"**可用工具**: {', '.join(allowed_tools)}")
            
            if category and category != "general":
                lines.append(f"**类别**: {category}")
            
            if tags:
                lines.append(f"**标签**: {', '.join(tags)}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def build_tools_section_text(
        self,
        max_items: Optional[int] = None
    ) -> str:
        """
        构建工具部分文本
        
        Args:
            max_items: 最大数量限制
        
        Returns:
            工具部分的 Markdown 文本
        """
        tools = self.get_tools_data()
        
        if not tools:
            return ""
        
        if max_items:
            tools = tools[:max_items]
        
        lines = ["## 可用工具 (Tools)", ""]
        
        for tool in tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            lines.append(f"- **{name}**: {description}")
        
        lines.append("")
        return "\n".join(lines)
    
    def build_mcp_section_text(self) -> str:
        """
        构建 MCP 服务器部分文本
        
        Returns:
            MCP 服务器部分的 Markdown 文本
        """
        servers = self.get_mcp_servers_data()
        
        if not servers:
            return ""
        
        lines = ["## 已连接的 MCP 服务", ""]
        
        for server in servers:
            name = server.get("name", "")
            status = server.get("status", "connected")
            instructions = server.get("instructions", "")
            tools = server.get("tools", [])
            
            lines.append(f"### {name}")
            lines.append(f"**状态**: {status}")
            
            if instructions:
                lines.append(f"**说明**: {instructions}")
            
            if tools:
                lines.append(f"**工具**: {', '.join(tools)}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算 Token 数
        
        Args:
            text: 要计算的文本
        
        Returns:
            Token 数量
        """
        if self.token_calc:
            return self.token_calc.count_tokens(text)
        else:
            logger.warning("Using fallback token estimation")
            return len(text) // 4
    
    def check_token_budget(
        self,
        capability_block: str,
        max_tokens: Optional[int] = None
    ) -> bool:
        """
        检查能力块是否超 Token 预算
        
        Args:
            capability_block: 能力块文本
            max_tokens: 最大 Token 数
        
        Returns:
            是否在预算内
        """
        max_tokens = max_tokens or self.MAX_CAPABILITY_TOKENS
        estimated_tokens = self.estimate_tokens(capability_block)
        
        if estimated_tokens > max_tokens:
            logger.warning(
                f"Capability block exceeds token budget: "
                f"{estimated_tokens} > {max_tokens}"
            )
            return False
        
        return True
    
    def build_compact_skills_text(self) -> str:
        """
        构建简化版技能文本（token 超预算时使用）
        
        Returns:
            简化版技能文本
        """
        skills = self.get_skills_data()
        
        if not skills:
            return ""
        
        skill_names = [s.get("name", "") for s in skills]
        return f"**技能**: {', '.join(skill_names)}"
    
    def build_compact_tools_text(self) -> str:
        """
        构建简化版工具文本
        
        Returns:
            简化版工具文本
        """
        tools = self.get_tools_data()
        
        if not tools:
            return ""
        
        tool_names = [t.get("name", "") for t in tools]
        return f"**工具**: {', '.join(tool_names)}"


global_capability_injector = CapabilityInjector()