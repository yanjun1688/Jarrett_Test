"""
Run Skill Tool
调用已有的 SkillExecuteView API 执行 skill
支持两种模式:
- generate: LLM 直接生成内容
- execute: LLM 解析意图,执行命令,返回结果
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import re
from pathlib import Path
import yaml
import os
import json

from asgiref.sync import sync_to_async

from core.tools.base_tool import BaseTool, ToolResult
from shared.utils.async_utils import async_run_command

logger = logging.getLogger(__name__)


def parse_mcp_text_content(text: str) -> str:
    """
    解析 MCP TextContent 格式，提取纯文本内容
    
    MCP CLI 返回格式如:
    [TextContent(type='text', text="### Ran Playwright code...", annotations=None, meta=None)]
    
    Args:
        text: 可能包含 MCP TextContent 格式的字符串
        
    Returns:
        提取出的纯文本内容
    """
    if not text or not isinstance(text, str):
        return text
    
    if 'TextContent(' not in text:
        return text
    
    text_parts = []
    
    pattern = r"TextContent\([^)]*text=['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, text)
    
    if matches:
        text_parts.extend(matches)
    
    if text_parts:
        return '\n\n'.join(text_parts)
    
    json_pattern = r'\[?\s*\{[^{}]*"type"\s*:\s*"text"[^{}]*"text"\s*:\s*"([^"]+)"[^{}]*\}\s*\]?'
    json_match = re.search(json_pattern, text)
    if json_match:
        try:
            json_str = json_match.group(0).replace("'", '"')
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                return '\n\n'.join([item.get('text', '') for item in parsed])
            return str(parsed.get('text', text))
        except json.JSONDecodeError:
            pass
    
    return text


class RunSkillTool(BaseTool):
    """执行已安装的 skill"""
    
    def __init__(self, llm_service: Optional[Any] = None) -> None:
        super().__init__(
            name="run_skill",
            description="执行已安装的 skill。当用户要求使用某个 skill 完成任务时调用。",
            version="1.0.0",
            timeout=120
        )
        self._llm_service = llm_service
    
    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "skill_name": {
                "type": "string",
                "description": "已安装的 skill 名称"
            },
            "user_input": {
                "type": "string",
                "description": "用户的任务需求"
            }
        }
    
    def _get_required_parameters(self) -> List[str]:
        return ["skill_name", "user_input"]
    
    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """解析 YAML frontmatter"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                pass
        return {}

    def _get_skill_mode(self, skill_content: str) -> str:
        """获取 skill 的执行模式
        
        判断优先级:
        1. 明确声明的 mode 字段
        2. 根据 allowed-tools 格式推断
           - Bash(pattern:*) 带参数模式 → execute (执行特定命令)
           - Bash 通用模式 → generate (辅助操作)
        3. 默认 generate
        """
        frontmatter = self._parse_frontmatter(skill_content)
        
        if "mode" in frontmatter:
            return str(frontmatter["mode"])
        
        allowed_tools = frontmatter.get("allowed-tools", "")
        if isinstance(allowed_tools, list):
            allowed_tools = " ".join(allowed_tools)
        
        if "Bash(" in allowed_tools:
            return "execute"
        
        return "generate"
    
    async def _execute_mode(
        self, 
        skill_name: str, 
        skill_content: str, 
        user_input: str, 
        llm_service: Any
    ) -> ToolResult:
        """执行模式: LLM 解析命令 -> subprocess 执行 -> 返回结果
        
        使用 JSON 结构化输出确保命令格式正确
        """
        skill_doc_preview = skill_content[:5000] if len(skill_content) > 5000 else skill_content
        
        system_prompt = f"""直接输出 JSON 命令数组，无解释，无 markdown 标记。

技能文档：
{skill_doc_preview}

输出示例：
{{"commands": ["agent-browser open https://google.com", "agent-browser wait --load networkidle", "agent-browser get text article"]}}

规则：
1. 只输出 JSON，以 {{ 开头，以 }} 结尾
2. 不要输出 ```json 或 ```
3. 不要输出解释或思考过程
4. 如果用户需要获取页面内容，最后一步使用 `agent-browser get text article` 或 `agent-browser get text main`
5. 如果用户只需要交互（点击、填表），使用 snapshot -i"""

        logger.info(f"[RunSkill][execute_mode] skill={skill_name}, skill_content={len(skill_content)}字符")
        
        try:
            response = await llm_service.generate(
                prompt=user_input,
                system_message=system_prompt,
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
        except TypeError:
            logger.warning("[RunSkill] LLM service 不支持 response_format 参数，回退到纯文本模式")
            return await self._execute_mode_legacy(skill_name, skill_content, user_input, llm_service)
        
        commands_text = response if isinstance(response, str) else str(response)
        logger.info(f"[RunSkill] LLM 原始输出: {commands_text[:500]}...")
        
        import re
        json_match = re.search(r'\{[^{}]*"commands"[^{}]*\[.*?\][^{}]*\}', commands_text, re.DOTALL)
        if json_match:
            commands_text = json_match.group(0)
            logger.info(f"[RunSkill] 提取的 JSON: {commands_text[:200]}...")
        else:
            logger.warning("[RunSkill] 未能提取 JSON，尝试直接解析")
        
        try:
            data = json.loads(commands_text)
            commands = data.get("commands", [])
        except json.JSONDecodeError as e:
            logger.error(f"[RunSkill] JSON 解析失败: {e}")
            logger.info("[RunSkill] 回退到 legacy 模式")
            return await self._execute_mode_legacy(skill_name, skill_content, user_input, llm_service)
        
        if not commands:
            return ToolResult(success=False, data={}, error="无法解析出可执行的命令")
        
        valid_commands = []
        for cmd in commands:
            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd.startswith("agent-browser") or cmd.startswith("npx"):
                valid_commands.append(cmd)
            else:
                logger.warning(f"[RunSkill] 跳过无效命令: {cmd}")
        
        if not valid_commands:
            return ToolResult(success=False, data={}, error="没有有效的可执行命令")
        
        results = []
        for cmd in valid_commands:
            logger.info(f"[RunSkill] 执行命令: {cmd}")
            result = await self._run_command(cmd)
            results.append({
                "command": cmd,
                "success": result["success"],
                "output": result.get("stdout", "") or result.get("output", ""),
                "error": result.get("error", "")
            })
        
        output_lines = []
        for r in results:
            status = "[OK]" if r["success"] else "[FAIL]"
            output_lines.append(f"{status} {r['command']}")
            if r["success"] and r["output"]:
                output_lines.append(r["output"][:10000])  # 提高限制，支持完整页面内容
            if not r["success"] and r["error"]:
                output_lines.append(f"Error: {r['error']}")
        
        result_text = "\n".join(output_lines)
        
        failed_commands = [r for r in results if not r["success"]]
        if failed_commands:
            error_details = "\n".join([
                f"  - {r['command']}: {r.get('error', '未知错误')}"
                for r in failed_commands[:3]
            ])
            error_msg = f"{len(failed_commands)}/{len(results)} 命令执行失败:\n{error_details}"
        else:
            error_msg = None
        
        return ToolResult(
            success=all(r["success"] for r in results),
            data={"skill_name": skill_name, "mode": "execute", "result": result_text, "commands": results},
            error=error_msg,
            metadata={"skill_name": skill_name, "mode": "execute", "result_length": len(result_text)}
        )
    
    async def _execute_mode_legacy(
        self,
        skill_name: str,
        skill_content: str,
        user_input: str,
        llm_service: Any
    ) -> ToolResult:
        """执行模式（旧版）：纯文本解析，兼容不支持 JSON 模式的 LLM"""
        system_prompt = f"""你是一个命令解析器。根据用户的任务需求，解析出需要执行的命令行命令。

## 技能指导文档

{skill_content}

---

## 输出格式（严格遵守）

输出必须是纯命令列表，格式如下：
```
agent-browser open https://example.com
agent-browser snapshot -i
agent-browser fill @e1 "text"
```

## 禁止输出的内容

不要输出任何思考过程、解释、分析
不要输出 "首先需要..."、"然后..."、"让我分析..."
不要输出中文解释或注释
不要输出 markdown 标记（如 #、```）
不要输出空行

## 输出规则

只输出可执行的 shell 命令
每行一个完整命令
命令必须是技能文档中定义的工具调用格式
"""
        
        response = await llm_service.generate(
            prompt=user_input,
            system_message=system_prompt,
            temperature=0.1,
            max_tokens=1024
        )
        
        commands_text = response if isinstance(response, str) else str(response)
        
        def _is_valid_command(line: str) -> bool:
            line = line.strip()
            if not line:
                return False
            if line.startswith('#') or line.startswith('```'):
                return False
            if '```' in line:
                return False
            if any(kw in line for kw in ['首先', '然后', '让我', '需要', '分析', '步骤', '注意', '解释']):
                return False
            if line.endswith('```'):
                return False
            if not any(tool in line for tool in ['agent-browser', 'npx', 'npm', 'git', 'python', 'pip', 'curl', 'echo', 'ls', 'cd', 'mkdir', 'rm', 'cat', 'mv']):
                return False
            return True
        
        commands = [cmd.strip() for cmd in commands_text.strip().split('\n') if _is_valid_command(cmd)]
        
        if not commands:
            return ToolResult(success=False, data={}, error="无法解析出可执行的命令")
        
        results = []
        for cmd in commands:
            logger.info(f"[RunSkill] 执行命令: {cmd}")
            result = await self._run_command(cmd)
            results.append({
                "command": cmd,
                "success": result["success"],
                "output": result.get("output", ""),
                "error": result.get("error", "")
            })
        
        output_lines = []
        for r in results:
            status = "[OK]" if r["success"] else "[FAIL]"
            output_lines.append(f"{status} `{r['command']}`")
            if r["success"] and r["output"]:
                output_lines.append(r["output"])
            if not r["success"] and r["error"]:
                output_lines.append(f"Error: {r['error']}")
        
        result_text = "\n".join(output_lines)
        
        failed_commands = [r for r in results if not r["success"]]
        if failed_commands:
            error_details = "\n".join([
                f"  - {r['command']}: {r.get('error', '未知错误')}"
                for r in failed_commands[:3]
            ])
            error_msg = f"{len(failed_commands)}/{len(results)} 命令执行失败:\n{error_details}"
        else:
            error_msg = None
        
        return ToolResult(
            success=all(r["success"] for r in results),
            data={"skill_name": skill_name, "mode": "execute", "result": result_text, "commands": results},
            error=error_msg,
            metadata={"skill_name": skill_name, "mode": "execute", "result_length": len(result_text)}
        )
    
    async def _run_command(self, command: str) -> Dict[str, Any]:
        """运行单个命令
        
        使用 async_run_command 统一接口，支持 Windows SelectorEventLoop 环境
        """
        import sys
        
        logger.info(f"[RunSkill] 准备执行命令: {command}")
        
        if sys.platform == 'win32':
            cmd_args = ['cmd', '/c', command]
        else:
            cmd_args = ['sh', '-c', command]
        
        result = await async_run_command(
            cmd_args,
            timeout=self.timeout
        )
        
        logger.info(f"[RunSkill] 命令完成 - 返回码: {result.get('returncode')}")
        if result.get("stdout"):
            logger.info(f"[RunSkill] stdout: {result['stdout'][:500]}")
        if result.get("stderr"):
            logger.info(f"[RunSkill] stderr: {result['stderr'][:500]}")
        
        if command.startswith("agent-browser"):
            if not result.get("success") and "超时" in str(result.get("error", "")):
                if result.get("stdout"):
                    logger.warning(f"[RunSkill] agent-browser 超时但有输出，视为成功")
                    result["success"] = True
                    result["error"] = None
            
            if result.get("stdout"):
                original_stdout = result["stdout"]
                parsed_stdout = parse_mcp_text_content(original_stdout)
                if parsed_stdout != original_stdout:
                    logger.info(f"[RunSkill] MCP TextContent 已解析")
                    result["stdout"] = parsed_stdout
                    result["output"] = parsed_stdout
        
        return result

    async def _generate_mode(
        self, 
        skill_name: str, 
        skill_content: str, 
        user_input: str, 
        llm_service: Any
    ) -> ToolResult:
        """生成模式: LLM 直接生成内容"""
        system_prompt = f"""你是一个专业的AI助手，现在需要根据以下技能指导来完成任务。

## 技能指导文档

{skill_content}

---

请根据技能指导文档的要求和最佳实践，完成用户的任务。确保输出内容符合技能文档中定义的标准和格式。
"""
        
        logger.info(f"[RunSkill][generate_mode] skill={skill_name}, skill_content={len(skill_content)}字符, system_prompt={len(system_prompt)}字符")
        
        response = await llm_service.generate(
            prompt=user_input,
            system_message=system_prompt,
            temperature=0.7,
            max_tokens=4096
        )
        
        result_text = response if isinstance(response, str) else str(response)
        
        return ToolResult(
            success=True,
            data={"skill_name": skill_name, "mode": "generate", "result": result_text},
            metadata={"skill_name": skill_name, "mode": "generate", "result_length": len(result_text)}
        )
    
    async def execute(self, **kwargs: Any) -> ToolResult:
        skill_name = kwargs.get("skill_name")
        user_input = kwargs.get("user_input")
        execution_logger = kwargs.get("_execution_logger")
        
        logger.info(f"[RunSkill] 开始执行 skill: skill_name={skill_name}, user_input={user_input[:50] if user_input else 'None'}...")
        
        if not skill_name:
            return ToolResult(success=False, data={}, error="缺少参数: skill_name")
        if not user_input:
            return ToolResult(success=False, data={}, error="缺少参数: user_input")
        
        if execution_logger:
            await sync_to_async(execution_logger.start)('skill', f'执行Skill: {skill_name}', f'正在执行 Skill "{skill_name}"')
        
        try:
            @sync_to_async
            def _get_skill_content():
                from django.conf import settings
                skill_path = Path(settings.BASE_DIR) / "skills" / skill_name / "SKILL.md"
                if not skill_path.exists():
                    return None, f"Skill '{skill_name}' 未安装或不存在，请先使用 install_skill 安装"
                return skill_path.read_text(encoding='utf-8'), None
            
            skill_content, error = await _get_skill_content()
            
            if error:
                logger.error(f"[RunSkill] Skill不存在: {error}")
                if execution_logger:
                    await sync_to_async(execution_logger.finish)({'status': 'error', 'error': error})
                return ToolResult(success=False, data={}, error=error)
            
            assert skill_content is not None
            logger.info(f"[RunSkill] Skill内容读取成功，长度: {len(skill_content)}")
            
            skill_mode = self._get_skill_mode(skill_content)
            logger.info(f"[RunSkill] Skill模式: {skill_mode}")
            
            llm_service = self._llm_service
            if llm_service is None:
                from core.agents.llm.base_llm import create_llm_service
                llm_service = create_llm_service(provider="qwen")
            
            if skill_mode == "execute":
                result = await self._execute_mode(skill_name, skill_content, user_input, llm_service)
            else:
                result = await self._generate_mode(skill_name, skill_content, user_input, llm_service)
            
            if execution_logger:
                await sync_to_async(execution_logger.finish)({
                    'status': 'success' if result.success else 'error',
                    'skill_name': skill_name,
                    'mode': skill_mode,
                    'has_result': bool(result.data)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Run skill failed: {e}")
            if execution_logger:
                await sync_to_async(execution_logger.finish)({'status': 'error', 'error': str(e)})
            return ToolResult(success=False, data={}, error=f"执行失败: {str(e)}")
