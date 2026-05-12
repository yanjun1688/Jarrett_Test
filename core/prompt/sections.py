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
- SkillsRegistrySection: Skills 注册表摘要
- ConversationHistorySection: 对话历史
- EnvironmentInfoSection: 环境信息

Reference: docs/2026/04/01/prompt_dynamic_assembly_design.md
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


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

优先使用工具满足用户需求：
- 用户请求涉及生成/执行/查询/保存 → 调用对应工具
- 用户请求是闲聊或感谢 → 直接回复

参数处理：
- 参数完整 → 调用工具
- 参数缺失但可合理推断 → 补全后调用
- 参数缺失且无法推断 → 询问用户

保存到项目的规则：
- 调用 save_test_script 或 save_test_case 前必须明确知道 project_id
- 如果不知道 project_id，先调用 query_projects 获取项目列表，列出选项让用户选择
- 禁止在未确认项目的情况下调用 save 工具
- 多个测试场景应合并为一个脚本保存（每个场景作为 steps 数组中的一个独立步骤），不要每个场景分别保存

脚本 JSON 结构示例（多场景合并）：
```json
{
  "name": "用户登录测试",
  "variables": {
    "base_url": "https://api.example.com",
    "valid_email": "user@test.com",
    "valid_pwd": "Test1234"
  },
  "steps": [
    {
      "name": "正确凭证登录",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/auth/login",
        "headers": {"Content-Type": "application/json"},
        "json": {"email": "{{valid_email}}", "password": "{{valid_pwd}}"}
      },
      "assertions": [{"type": "jsonpath", "expression": "$.code", "expected": 200}]
    },
    {
      "name": "错误密码登录",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/auth/login",
        "headers": {"Content-Type": "application/json"},
        "json": {"email": "{{valid_email}}", "password": "wrong_pwd"}
      },
      "assertions": [{"type": "jsonpath", "expression": "$.code", "expected": 400}]
    }
  ]
}
```

执行规则：
- 保存的脚本 JSON 中不应包含 stop_on_failure 字段，保证断言失败后继续执行后续步骤
- 断言优先用 jsonpath 验证业务状态码（$.code），除非需要验证 HTTP 响应码（如 401）才用 status_code

知识库范围：仅包含用户上传的项目文档。

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

### ReAct 任务完成规则

1. **任务完成即停止**
   - 当所有用户请求的操作都已成功执行（工具返回 success=True），**立即停止**调用工具，直接回复用户
   - 不要重复执行已经成功的操作
   - 不要为了"验证"而重新执行已完成的操作

2. **一次到位**
   - 能不调用工具就不要调用
   - 如果用户只让"打开百度"，打开后直接回复"已打开"，不要继续做其他操作
   - 如果工具返回了预期结果，认为该操作已完成

3. **向用户展示选项时必须附带名称**
   - 当工具返回了选项列表（如项目列表），向用户展示时**必须同时展示编号和名称**
   - 正确示例："请选择项目：\\n- [1] 真实压测测试项目\\n- [2] crAPI压力测试项目"
   - 错误示例："请选择项目 ID（1-2）"（用户看不到名称）

### 生成测试用例规则

1. 用户要求"生成测试"、"写个用例"等 → **必须调用 generate_api_test / generate_ui_test / generate_test 工具**
2. 不要自己编示例，让工具生成
3. project_id 在保存时才需要，生成时不需要

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
- 查找/浏览 skill 文件（应使用 load_skill 工具）
- 复杂的正则替换

### Skills 使用规则

- skill 文件位于 `skills/` 目录，由系统管理
- 需要获取某 skill 的完整指令时，使用 `load_skill` 工具，不要用 bash 去磁盘查找
- 找不到的 skill 可以使用 `install_skill` 工具从 GitHub/skills.sh 安装

### 并行调用

- 没有依赖关系的工具调用要并行
- 例如：同时读取多个文件
- 例如：同时执行多个搜索

### 浏览器操作

浏览器操作必须使用 mcp__playwright__* 工具：

| 操作 | 必须使用 | 禁止使用 |
|------|---------|---------|
| 打开网页 | mcp__playwright__browser_navigate | bash + agent-browser |
| 点击元素 | mcp__playwright__browser_click | bash + agent-browser |
| 输入文本 | mcp__playwright__browser_type | bash + agent-browser |
| 获取页面内容 | mcp__playwright__browser_snapshot | bash + agent-browser |
| 填充表单 | mcp__playwright__browser_fill_form | bash + agent-browser |"""


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


class SkillsRegistrySection(PromptSection):
    """Skills 注册表模块 — 渲染技能名称+描述摘要，完整内容通过 load_skill 工具按需获取"""

    @property
    def name(self) -> str:
        return "skills_registry"

    @property
    def is_static(self) -> bool:
        return False

    def should_include(self, context: Dict[str, Any]) -> bool:
        return bool(context.get("include_skills", True))

    def render(self, context: Dict[str, Any]) -> str:
        skills = context.get("installed_skills")

        if not skills:
            return """### Skills 扩展能力

当前未安装任何 skill。可以使用 install_skill 工具安装：
- testcase-generator: 测试用例生成器
- agent-browser: 浏览器自动化
- api-design-principles: API 设计原则
- webapp-testing: Web 应用测试"""

        lines = ["## Skills 扩展能力", ""]
        lines.append("所有 skill 文件位于 `skills/` 目录（由系统管理，不要用 bash 去磁盘查找）。")
        lines.append("需要完整指令时请调用 `load_skill` 工具获取：")
        lines.append("")
        for s in skills:
            name = s.get("name", "")
            desc = s.get("description", "")
            tools = s.get("allowed_tools", [])

            lines.append(f"- **{name}**: {desc}")
            if tools:
                lines.append(f"  可用工具: {', '.join(tools)}")

        lines.append("")
        lines.append("使用 `load_skill(name=\"<skill_name>\")` 获取完整技能指令。")
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
        return bool(context.get("include_conversation_history", True))
    
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
    """环境信息模块 - 包含 test_type 强制指令（方案C）"""
    
    @property
    def name(self) -> str:
        return "environment_info"
    
    @property
    def is_static(self) -> bool:
        return False
    
    def should_include(self, context: Dict[str, Any]) -> bool:
        # 当有 test_type、平台信息或其他环境信息时才包含
        return bool(context.get("test_type") or context.get("project_path") or 
                    context.get("language") or context.get("test_framework") or 
                    context.get("working_directory") or context.get("platform"))
    
    def render(self, context: Dict[str, Any]) -> str:
        lines = ["### 环境信息", ""]
        
        # 方案C：test_type 强制指令（Prompt注入）
        test_type = context.get("test_type")
        if test_type:
            tool_mapping = {
                'ui': ('generate_ui_test', 'UI/Web 自动化测试', 'Playwright'),
                'api': ('generate_api_test', 'API/接口测试', 'JSON 配置'),
                'prd': ('generate_test', 'PRD文档测试用例', '测试用例分析'),
            }
            tool_name, test_desc, framework = tool_mapping.get(test_type, ('unknown', '未知类型', ''))
            
            lines.append(f"**当前测试类型**: **{test_desc}**")
            lines.append(f"- **推荐工具**: `{tool_name}`")
            lines.append(f"- **框架**: {framework}")
            lines.append("")
            
            if context.get("project_id"):
                lines.append(f"- 项目ID: {context['project_id']}（已自动填充）")
        
        if context.get("project_path"):
            lines.append(f"- 项目路径: {context['project_path']}")
        
        if context.get("language"):
            lines.append(f"- 语言: {context['language']}")
        
        if context.get("test_framework"):
            lines.append(f"- 测试框架: {context['test_framework']}")
        
        if context.get("working_directory"):
            lines.append(f"- 工作目录: {context['working_directory']}")

        if context.get("platform"):
            lines.append(f"- 运行平台: {context['platform']}")

        return "\n".join(lines)
