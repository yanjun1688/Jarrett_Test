"""
ReAct Engine — 标准 ReAct 多轮循环引擎

依赖：
- ToolRegistry: 工具注册和查找
- BaseLLMService: LLM 调用（generate_with_tools）

不关心 prompt 构建、对话历史存储、技能注入 — 这些由 ChatbotAgent 负责。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from core.tools.base_tool import ToolRegistry, ToolResult

import logging

logger = logging.getLogger(__name__)


@dataclass
class ReActResult:
    response: str
    tool_calls_made: int = 0
    iterations: int = 0
    stopped_reason: str = "complete"  # complete | max_iters | failures | error
    options: Optional[List[Dict[str, Any]]] = None
    internal_messages: Optional[List[Dict[str, Any]]] = None


class ReActEngine:
    """标准 ReAct 循环 — 依赖 ToolRegistry + BaseLLMService，不关心 prompt 构建"""

    def __init__(
        self,
        registry: ToolRegistry,
        llm_service: Any,
        max_iterations: int = 10,
        max_consecutive_failures: int = 3,
        max_result_chars: int = 8000,
    ):
        self.registry = registry
        self.llm = llm_service
        self.max_iterations = max_iterations
        self.max_consecutive_failures = max_consecutive_failures
        self.max_result_chars = max_result_chars

    async def run(
        self,
        user_message: str,
        system_prompt: str,
        history: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> ReActResult:
        """ReAct 循环"""
        messages = self._build_messages(system_prompt, history, user_message)
        consecutive_failures = 0
        total_tool_calls = 0
        last_options: Optional[List[Dict[str, Any]]] = None
        internal_messages: List[Dict[str, Any]] = []

        tool_names = [t.get("function", {}).get("name", "?") for t in tools]
        logger.info(f"[ReAct] === 开始 === user_message={user_message[:100]!r}")
        logger.info(f"[ReAct] 可用工具({len(tool_names)}): {tool_names}")
        logger.info(f"[ReAct] 历史消息数: {len(history)}, 构建后消息数: {len(messages)}")

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"[ReAct] ─── 迭代 {iteration}/{self.max_iterations} ───")
            logger.info(f"[ReAct] 发送给 LLM: {len(messages)} 条消息, {len(tools)} 个工具")

            result = await self.llm.generate_with_tools(
                prompt=None,
                tools=tools,
                system_message=None,
                conversation_history=messages,
            )

            tool_calls = result.get("tool_calls")
            llm_text = result.get("response", "")
            logger.info(f"[ReAct] LLM 返回: text={llm_text[:200]!r}, tool_calls={len(tool_calls) if tool_calls else 0}")

            if not tool_calls:
                logger.info(f"[ReAct] === 结束 === LLM 直接回复, 共 {iteration} 轮, {total_tool_calls} 次工具调用")
                return ReActResult(
                    response=llm_text,
                    tool_calls_made=total_tool_calls,
                    iterations=iteration,
                    options=last_options,
                    internal_messages=internal_messages,
                )

            # Append assistant message with canonical tool_calls
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": llm_text}
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    self._extract_tool_call(tc) for tc in tool_calls
                ]
            messages.append(assistant_msg)
            internal_messages.append(assistant_msg)

            for tc in tool_calls:
                info = self._extract_tool_call(tc)
                name, args, tc_id = info["name"], info["arguments"], info["id"]
                logger.info(f"[ReAct] ▶ 执行工具: {name}(id={tc_id})")
                logger.info(f"[ReAct]   参数: {json.dumps(args, ensure_ascii=False, default=str)[:500]}")

                tool = self.registry.get(name)
                if not tool:
                    logger.warning(f"[ReAct] ✗ 工具不存在: {name}")
                    tool_msg = self._append_tool_msg(messages, tc_id, f"Error: unknown tool '{name}'")
                    if tool_msg:
                        internal_messages.append(tool_msg)
                    consecutive_failures += 1
                    continue

                try:
                    tr = await tool.execute_with_validation(**args)
                except Exception as e:
                    logger.error(f"[ReAct] ✗ 工具异常: {name} -> {e}", exc_info=True)
                    tool_msg = self._append_tool_msg(messages, tc_id, f"Error: {e}")
                    if tool_msg:
                        internal_messages.append(tool_msg)
                    consecutive_failures += 1
                    continue

                text = self._format(tr)
                text = self._truncate(text)
                status_icon = "✓" if tr.success else "✗"
                logger.info(f"[ReAct] {status_icon} 工具结果: {name} -> success={tr.success}")
                logger.info(f"[ReAct]   结果内容: {text[:300]!r}")
                tool_msg = self._append_tool_msg(messages, tc_id, text)
                if tool_msg:
                    internal_messages.append(tool_msg)
                total_tool_calls += 1

                consecutive_failures = 0 if tr.success else consecutive_failures + 1

                # 捕获工具返回的选项列表（如项目列表），用于前端直接渲染
                if tr.success and isinstance(tr.data, dict) and "options" in tr.data:
                    last_options = tr.data["options"]

            if consecutive_failures >= self.max_consecutive_failures:
                logger.error(f"[ReAct] === 结束 === 连续 {consecutive_failures} 次失败, 共 {iteration} 轮")
                return ReActResult(
                    response="多次工具调用失败，请检查系统状态后重试。",
                    tool_calls_made=total_tool_calls,
                    iterations=iteration,
                    stopped_reason="failures",
                    options=last_options,
                    internal_messages=internal_messages,
                )

            messages = self._compact_messages(messages)

        logger.warning(f"[ReAct] === 结束 === 达到最大轮次 {self.max_iterations}, 共 {total_tool_calls} 次工具调用")
        return ReActResult(
            response="任务超过最大执行轮次，部分操作可能未完成。",
            tool_calls_made=total_tool_calls,
            iterations=self.max_iterations,
            stopped_reason="max_iters",
            options=last_options,
            internal_messages=internal_messages,
        )

    # ── helpers ──

    def _build_messages(
        self,
        system_prompt: str,
        history: List[Dict[str, Any]],
        user_msg: str,
    ) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
            logger.info(f"[ReAct] system_prompt: {len(system_prompt)} 字符, 前200字: {system_prompt[:200]!r}")
        for h in history:
            role = h.get("role", "")
            content = h.get("content")
            if role == "system" and content:
                msgs.append({"role": "system", "content": content})
            elif role in ("user", "assistant", "tool") and content:
                if role == "tool":
                    msgs.append({
                        "role": "tool",
                        "tool_call_id": h.get("tool_call_id", ""),
                        "content": content,
                    })
                else:
                    msg: Dict[str, Any] = {"role": role, "content": content}
                    if role == "assistant" and h.get("tool_calls"):
                        msg["tool_calls"] = h["tool_calls"]
                    msgs.append(msg)
        msgs.append({"role": "user", "content": user_msg})
        logger.info(f"[ReAct] _build_messages: system={1 if system_prompt else 0}, history={len(history)} -> msgs={len(msgs)}")
        return msgs

    def _extract_tool_call(self, tc: Any) -> Dict[str, Any]:
        if isinstance(tc, dict):
            return {
                "id": str(tc.get("id", "")),
                "name": str(tc.get("name", "unknown")),
                "arguments": tc.get("arguments") if "arguments" in tc else tc.get("input", {}),
            }
        if hasattr(tc, "function"):
            func_args: Any = tc.function.arguments
            if isinstance(func_args, str):
                try:
                    func_args = json.loads(func_args)
                except (json.JSONDecodeError, TypeError):
                    func_args = {}
            return {
                "id": str(getattr(tc, "id", "")),
                "name": str(tc.function.name),
                "arguments": func_args if isinstance(func_args, dict) else {},
            }
        return {
            "id": "",
            "name": str(getattr(tc, "name", "unknown")),
            "arguments": {},
        }

    def _format(self, tr: ToolResult) -> str:
        if not tr.success:
            return f"Error: {tr.error}"
        d: Any = tr.data
        if isinstance(d, str):
            return d
        if isinstance(d, dict):
            if "options" in d:
                lines = [d.get("message", ""), ""]
                for opt in d["options"]:
                    oid = opt.get("id", "")
                    label = opt.get("label", "")
                    lines.append(f"- [{oid}] {label}")
                return "\n".join(lines)
            for k in ("result", "message", "answer"):
                if k in d:
                    return str(d[k])
            return json.dumps(d, ensure_ascii=False, default=str)
        return str(d)

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_result_chars:
            return text
        half = self.max_result_chars // 2
        return (
            text[:half]
            + f"\n\n... [省略 {len(text) - self.max_result_chars} 字符] ...\n\n"
            + text[-half:]
        )

    def _append_tool_msg(
        self,
        messages: List[Dict[str, Any]],
        tc_id: str,
        content: str,
    ) -> Dict[str, Any]:
        msg = {"role": "tool", "tool_call_id": tc_id, "content": content}
        messages.append(msg)
        return msg

    def _compact_messages(
        self,
        messages: List[Dict[str, Any]],
        max_messages: int = 20,
        keep_recent: int = 6,
    ) -> List[Dict[str, Any]]:
        """超过阈值时裁剪消息列表，保留 system prompt 和最近消息，中间截断"""
        if len(messages) <= max_messages:
            return messages

        # Collect leading system prompts by role, not by position (BUG 7 fix)
        system: List[Dict[str, Any]] = []
        idx = 0
        while idx < len(messages) and messages[idx].get("role") == "system":
            system.append(messages[idx])
            idx += 1

        recent = messages[-keep_recent:]
        middle = messages[idx:-keep_recent]

        # Remove previous compaction summaries to avoid accumulation (BUG 6 fix)
        middle = [
            m for m in middle
            if not (m.get("role") == "system" and "[上下文裁剪]" in str(m.get("content", "")))
        ]

        user_c = sum(1 for m in middle if m.get("role") == "user")
        asst_c = sum(1 for m in middle if m.get("role") == "assistant")
        tool_c = sum(1 for m in middle if m.get("role") == "tool")

        tool_names: list[str] = []
        for m in middle:
            tcs = m.get("tool_calls", [])
            for tc in tcs:
                tn = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                if tn and tn not in tool_names:
                    tool_names.append(tn)

        tool_info = f"已执行: {', '.join(tool_names)}" if tool_names else ""

        logger.info(
            f"[ReAct] 消息裁剪: {len(messages)} -> {len(system) + 1 + keep_recent} "
            f"(省略 {user_c} 用户/{asst_c} 助手/{tool_c} 工具) {tool_info}"
        )

        summary = {
            "role": "system",
            "content": (
                f"[上下文裁剪] 省略了 {user_c} 条用户消息、{asst_c} 条助手回复、"
                f"{tool_c} 次工具调用。{tool_info}。继续当前任务。"
            ),
        }
        return system + [summary] + recent
