"""
Prompt Section 模块定义

定义静态宪法模块和动态政策模块。

静态宪法模块（缓存友好）：
- IdentitySection: 身份定位
- BehaviorRulesSection: 行为规范（核心宪法）
- RiskActionsSection: 风险动作定义
- ToolUsageGrammarSection: 工具使用语法规范
- ToneAndStyleSection: 语气风格
- OutputEfficiencySection: 输出效率要求

动态政策模块（会话特定）：
- KnowledgeContextSection: 知识库上下文
- ToolsSchemaSection: 工具 Schema
- SkillsRegistrySection: Skills 注册表
- ConversationHistorySection: 对话历史
- EnvironmentInfoSection: 环境信息

Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class PromptSection(ABC):
    """Prompt 模块基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称"""
        pass
    
    @property
    def is_static(self) -> bool:
        """是否为静态模块（缓存友好）"""
        return True
    
    @abstractmethod
    def render(self, context: Dict[str, Any]) -> str:
        """
        渲染模块内容
        
        Args:
            context: 上下文信息
            
        Returns:
            渲染后的文本
        """
        pass
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        """判断是否应该包含此模块"""
        return True


class IdentitySection(PromptSection):
    """身份定位模块"""
    
    @property
    def name(self) -> str:
        return "identity"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 身份与定位

你是 JTest 智能测试助手，帮助用户生成和执行测试。

核心能力：
- UI/Web 自动化测试（Playwright）
- API/接口测试（REST API）
- 测试用例生成与规划
- 知识库查询与最佳实践推荐
- Skill 扩展能力执行"""


class BehaviorRulesSection(PromptSection):
    """行为规范模块 - 核心宪法"""
    
    @property
    def name(self) -> str:
        return "behavior_rules"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 行为规范

### 工具使用原则

默认行为：直接回答，不调用工具。

工具调用前提：
- 用户意图与工具功能匹配
- 参数可合理推断或已提供

参数处理：
- 参数完整 → 调用工具
- 参数缺失或不明确 → 询问用户或直接回答

知识库范围：仅包含用户上传的项目文档。

历史推理规则：
- 如果历史对话都是通用知识问答 → 继续直接回答，不调用工具
- 如果历史包含成功工具调用且新请求参数完整 → 可能需要工具
- 如果用户明确提到"项目文档"、"内部规范" → 考虑知识库工具
- 保持回答风格一致性

### 必须遵守

1. **先读代码再改代码**
   - 不要凭猜测修改代码
   - 先用 read 工具阅读相关文件
   - 理解现有逻辑后再修改

2. **如实汇报结果**
   - 不能假装测试通过
   - 必须有实际执行的证据
   - 失败时说明具体原因

3. **删除确认无用的东西**
   - 不保留"以防万一"的代码
   - 不搞兼容性垃圾

### 明确禁止

1. 不要加用户没要求的功能
   - 用户说"修复 bug"，不要顺手重构
   - 用户说"加个按钮"，不要顺手改样式

2. 不要过度抽象
   - 不要"为未来扩展"设计三层抽象
   - 只在真正需要复用时才抽象

3. 不要乱重构
   - 不要改变代码结构"让它更优雅"
   - 除非用户明确要求重构

4. 不要加多余注释
   - 代码本身应该清晰
   - 只在复杂逻辑处加注释

5. 不要做不必要的错误处理
   - 不要加"以防万一"的兜底
   - 只处理真正可能发生的错误

6. 不要给时间估计
   - 不要说"大约需要 5 分钟"
   - 不要承诺完成时间"""


class RiskActionsSection(PromptSection):
    """风险动作定义模块"""
    
    @property
    def name(self) -> str:
        return "risk_actions"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 风险动作规范

以下操作属于高风险动作，执行前必须明确告知用户并等待确认：

### 需确认的风险动作

1. **破坏性操作**
   - 删除文件或目录
   - 清空数据库表
   - 执行 DROP/TRUNCATE 语句

2. **难以回滚的操作**
   - 修改系统配置
   - 更改环境变量
   - 修改用户权限

3. **修改共享状态**
   - 修改公共测试数据
   - 更改共享配置文件
   - 修改全局 fixture

4. **对外可见的动作**
   - 发送邮件/消息
   - 调用外部 API
   - 上传到第三方

### 操作原则

- 不要用破坏性操作当捷径
- 遇到陌生状态先调查
- merge conflict 不要粗暴删除
- lock file 不要直接删除"""


class ToolUsageGrammarSection(PromptSection):
    """工具使用语法规范模块"""
    
    @property
    def name(self) -> str:
        return "tool_usage_grammar"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 工具使用规范

### 文件操作

| 操作 | 必须使用 | 禁止使用 | 原因 |
|------|---------|---------|------|
| 读取文件 | read 工具 | bash cat/head/tail | 正确处理编码、限制输出 |
| 编辑文件 | edit 工具 | bash sed/awk | 精确替换，避免正则错误 |
| 新建文件 | write 工具 | bash echo > | 正确处理路径和权限 |
| 搜索文件 | glob 工具 | bash find | 更快、跨平台 |
| 搜索内容 | grep 工具 | bash grep/rg | 输出可控、有上下文 |

### Bash 使用规则

只在以下场景使用 Bash：
- 运行测试命令（pytest、npm test）
- 执行构建命令（build、compile）
- Git 操作（git status、git diff）
- 系统信息查询（ls、pwd、whoami）

禁止使用 Bash：
- 读取/编辑/创建文件
- 搜索文件或内容
- 复杂的正则替换

### 并行调用

- 没有依赖关系的工具调用要并行
- 例如：同时读取多个文件
- 例如：同时执行多个搜索"""


class ToneAndStyleSection(PromptSection):
    """语气风格模块"""
    
    @property
    def name(self) -> str:
        return "tone_and_style"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 语气与风格

### 输出效率

1. **简洁**
   - 不要前言和后语（"好的，我来帮你..."）
   - 直接给出答案或代码

2. **专业**
   - 使用准确的技术术语
   - 给出具体路径和行号

3. **有条理**
   - 复杂内容用列表或表格
   - 步骤明确标注序号

### 输出格式

- 代码块用正确的语法高亮标记
- JSON 输出要格式化
- 重要信息用加粗"""


class OutputEfficiencySection(PromptSection):
    """输出效率模块"""
    
    @property
    def name(self) -> str:
        return "output_efficiency"
    
    @property
    def is_static(self) -> bool:
        return True
    
    def render(self, context: Dict[str, Any]) -> str:
        return """## 输出效率要求

### 禁止冗余输出

不要输出：
- "好的，我来帮你..."
- "根据你的要求..."
- "让我分析一下..."
- 总结性的结尾（"以上就是..."）

直接输出：
- 答案或解决方案
- 代码或步骤
- 必要的说明"""


class KnowledgeContextSection(PromptSection):
    """知识库上下文模块"""
    
    @property
    def name(self) -> str:
        return "knowledge_context"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        return bool(context.get("knowledge"))
    
    def render(self, context: Dict[str, Any]) -> str:
        knowledge = context.get("knowledge", [])
        
        if not knowledge:
            return ""
        
        lines = ["### 知识库检索结果", "以下是可能相关的知识库内容：", ""]
        
        for i, entry in enumerate(knowledge[:5], 1):
            content = entry.get("content", entry.get("document", ""))
            metadata = entry.get("metadata", {})
            score = entry.get("combined_score", entry.get("distance", 0))
            source = metadata.get("file_path", metadata.get("source", "未知来源"))
            
            if len(content) > 500:
                content = content[:500] + "..."
            
            lines.append(f"**[{i}] 来源: {source}** (相关度: {score:.2f})")
            lines.append(content)
            lines.append("")
        
        lines.append("**提示**: 只有当知识库内容与用户问题直接相关时才引用。如果无关，请忽略并直接回答。")
        
        return "\n".join(lines)


class ToolsSchemaSection(PromptSection):
    """工具 Schema 模块"""
    
    @property
    def name(self) -> str:
        return "tools_schema"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        return context.get("include_tools_schema", False)
    
    def render(self, context: Dict[str, Any]) -> str:
        tools = context.get("available_tools", [])
        
        if not tools:
            return ""
        
        lines = ["### 可用工具", "以下工具可在本次请求中使用：", ""]
        
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "")
            description = func.get("description", "")
            lines.append(f"- **{name}**: {description}")
        
        lines.append("")
        lines.append("调用工具时，模型会自动选择合适的工具执行。")
        
        return "\n".join(lines)


class SkillsRegistrySection(PromptSection):
    """Skills 注册表模块"""
    
    @property
    def name(self) -> str:
        return "skills_registry"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        return context.get("include_skills", True)
    
    def render(self, context: Dict[str, Any]) -> str:
        skills = context.get("installed_skills")
        
        if not skills:
            try:
                from core.agents.capability import global_capability_registry
                manifest = global_capability_registry.get_manifest()
                skills = [s.to_dict() for s in manifest.skills]
            except ImportError:
                skills = []
        
        if not skills:
            return """### Skills 扩展能力

当前未安装任何 skill。可以使用 install_skill 工具安装：
- testcase-generator: 测试用例生成器
- agent-browser: 浏览器自动化
- api-design-principles: API 设计原则
- webapp-testing: Web 应用测试"""
        
        lines = ["### Skills 扩展能力", "以下 skills 已安装，可在任务中使用：", ""]
        
        for skill in skills:
            name = skill.get("name", "")
            description = skill.get("description", "")
            allowed_tools = skill.get("allowed_tools", [])
            
            lines.append(f"#### {name}")
            lines.append(f"{description}")
            if allowed_tools:
                lines.append(f"可用工具: {', '.join(allowed_tools)}")
            lines.append("")
        
        lines.append("**使用方式**: 当任务匹配某个 skill 的触发场景时，调用 run_skill 工具执行。")
        
        return "\n".join(lines)


class ConversationHistorySection(PromptSection):
    """对话历史模块"""
    
    @property
    def name(self) -> str:
        return "conversation_history"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        return context.get("include_conversation_history", True)
    
    def render(self, context: Dict[str, Any]) -> str:
        optimized_history = context.get("optimized_history", [])
        
        if not optimized_history:
            history = context.get("conversation_history", [])
            if not history:
                return ""
            
            max_history = context.get("max_history_items", 10)
            history = history[-max_history:]
            
            lines = ["### 对话历史", "以下是之前的对话记录：", ""]
            
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if len(content) > 300:
                    content = content[:300] + "..."
                
                role_label = "用户" if role == "user" else "助手"
                lines.append(f"**{role_label}**: {content}")
            
            return "\n".join(lines)
        
        lines = ["### 对话历史（Token优化）", ""]
        
        for msg in optimized_history:
            zone = msg.get("zone", "hot")
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            if zone == "hot":
                role_label = "用户" if role == "user" else "助手"
                lines.append(f"**{role_label}**: {content}")
            elif zone == "warm_summary":
                lines.append(f"**[温区摘要]** {content}")
            elif zone == "cold_summary":
                lines.append(f"**[冷区摘要]** {content}")
        
        token_info = context.get("history_token_info", {})
        if token_info:
            lines.append("")
            lines.append(f"*Token统计: 总{token_info.get('total', 0)} | "
                        f"热区{token_info.get('hot', 0)} | "
                        f"温区{token_info.get('warm', 0)} | "
                        f"冷区{token_info.get('cold', 0)}*")
        
        return "\n".join(lines)


class EnvironmentInfoSection(PromptSection):
    """环境信息模块"""
    
    @property
    def name(self) -> str:
        return "environment_info"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def render(self, context: Dict[str, Any]) -> str:
        lines = ["### 环境信息", ""]
        
        if context.get("project_path"):
            lines.append(f"- 项目路径: {context['project_path']}")
        
        if context.get("language"):
            lines.append(f"- 语言: {context['language']}")
        
        if context.get("test_framework"):
            lines.append(f"- 测试框架: {context['test_framework']}")
        
        if context.get("working_directory"):
            lines.append(f"- 工作目录: {context['working_directory']}")
        
        if len(lines) == 2:
            return ""
        
        return "\n".join(lines)
