"""
Skill Loader — 技能扫描和元数据解析

此模块只负责扫描技能目录、解析 SKILL.md 的 YAML frontmatter。
不执行、不注册、不创建 Skill 对象。

设计原则：
- 纯数据：SkillInfo 是纯数据类，无执行逻辑
- 缓存：discover() 自动缓存，启动时调用一次
- 多目录：支持内置和用户技能目录
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
import logging

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    """技能数据 — 纯数据，无执行逻辑"""
    name: str
    description: str
    content: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""


class SkillLoader:
    """技能加载器 — 只扫描+解析，不执行、不注册"""

    _shared_cache: Dict[str, List[SkillInfo]] = {}  # 类级缓存，所有实例共享

    def __init__(self, skill_dirs: List[str]):
        self.skill_dirs = [Path(d) for d in skill_dirs]
        self._cache_key = str(sorted(str(d) for d in self.skill_dirs))

    def discover(self) -> List[SkillInfo]:
        """扫描所有技能目录，返回 SkillInfo 列表（自动缓存）"""
        if self._cache_key in self._shared_cache:
            return self._shared_cache[self._cache_key]

        results: List[SkillInfo] = []
        for sd in self.skill_dirs:
            if not sd.exists():
                continue
            for entry in sd.iterdir():
                if not entry.is_dir():
                    continue
                md = entry / "SKILL.md"
                if not md.exists():
                    continue
                raw = md.read_text(encoding="utf-8")
                fm = self._parse_frontmatter(raw)
                content = self._extract_body(raw)
                results.append(SkillInfo(
                    name=fm.get("name", entry.name),
                    description=fm.get("description", ""),
                    content=content,
                    allowed_tools=fm.get("allowed-tools", []),
                    version=fm.get("version", "1.0.0"),
                    author=fm.get("author", ""),
                ))
        self._shared_cache[self._cache_key] = results
        return results

    @classmethod
    def invalidate_cache(cls) -> None:
        """清除所有 SkillLoader 实例的缓存，下次 discover() 重新扫描目录"""
        cls._shared_cache.clear()
        logger.info("[SkillLoader] 全局缓存已失效")

    def _parse_frontmatter(self, raw: str) -> Dict[str, Any]:
        match = re.match(r"^---\n(.*?)\n---", raw, re.DOTALL)
        return yaml.safe_load(match.group(1)) or {} if match else {}

    def _extract_body(self, raw: str) -> str:
        match = re.match(r"^---\n.*?\n---\n?", raw, re.DOTALL)
        return raw[match.end():].strip() if match else raw
