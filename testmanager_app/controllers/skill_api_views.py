"""
Skill API 视图
封装 npx skills 命令，提供搜索、安装、执行功能
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import subprocess
import json
import re
import time
import asyncio
from pathlib import Path
import logging

from django.conf import settings
from core.agents.skill_loader import SkillLoader
from core.agents.llm.base_llm import create_llm_service
from shared.utils import get_npx_command

logger = logging.getLogger(__name__)

SKILL_DIR = Path(settings.BASE_DIR) / "skills"
AGENT_SKILL_DIR = Path(settings.BASE_DIR) / ".agents" / "skills"


class SkillRemoteSearchView(APIView):
    """搜索远程技能"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        keyword = request.query_params.get('keyword', '').strip()
        if not keyword:
            return Response({
                "success": False,
                "error": "请输入搜索关键词"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 输入格式校验：只允许安全字符
        if not re.match(r'^[a-zA-Z0-9@/._\- ]+$', keyword):
            return Response({
                "success": False,
                "error": "搜索关键词包含非法字符"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            npx_cmd = get_npx_command()
            if not npx_cmd:
                return Response({
                    "success": False,
                    "error": "npx not found in PATH"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            result = subprocess.run(
                [npx_cmd, 'skills', 'find', keyword, '--json'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            if result.returncode != 0:
                return Response({
                    "success": False,
                    "error": result.stderr or "搜索失败"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            skills = self._parse_skills_output(result.stdout)
            return Response({
                "success": True,
                "data": {"skills": skills}
            })
            
        except subprocess.TimeoutExpired:
            return Response({
                "success": False,
                "error": "搜索超时，请稍后重试"
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except Exception as e:
            logger.error(f"Search remote skills error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _parse_skills_output(self, output: str) -> list[dict[str, Any]]:
        """解析 npx skills find 输出"""
        if not output:
            return []
        try:
            data = json.loads(output)
            if isinstance(data, dict) and 'skills' in data:
                return data['skills']
            elif isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            lines = output.strip().split('\n')
            skills = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if parts:
                        skills.append({
                            "id": parts[0] if len(parts) > 0 else "",
                            "name": parts[0].split('@')[-1] if len(parts) > 0 else "",
                            "description": ' '.join(parts[1:]) if len(parts) > 1 else ""
                        })
            return skills


class SkillLocalListView(APIView):
    """获取本地已安装技能列表（内置 + 用户安装）"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        try:
            loader = SkillLoader(
                skill_dir=str(SKILL_DIR),
                extra_skill_dirs=[str(AGENT_SKILL_DIR)]
            )
            skill_names = loader.scan_skills()
            
            skills = []
            for name in skill_names:
                info = loader.get_skill_info(name)
                if info:
                    skill_path = Path(info.get('path', ''))
                    info['source'] = 'builtin' if skill_path.is_relative_to(SKILL_DIR) else 'user_installed'
                    skills.append(info)
            
            return Response({
                "success": True,
                "data": {"skills": skills}
            })
            
        except Exception as e:
            logger.error(f"Get local skills error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SkillInstallView(APIView):
    """安装远程技能到本地（.agent/skills/ 目录）"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request: Request) -> Response:
        skill_name = request.data.get('skill_name')
        if not skill_name:
            return Response({
                "success": False,
                "error": "请提供 skill_name"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not re.match(r'^[a-zA-Z0-9@/._\-]+$', skill_name):
            return Response({
                "success": False,
                "error": "skill_name 包含非法字符"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            npx_cmd = get_npx_command()
            if not npx_cmd:
                return Response({
                    "success": False,
                    "error": "npx not found in PATH"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            result = subprocess.run(
                [npx_cmd, 'skills', 'add', skill_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
                cwd=str(settings.BASE_DIR)
            )
            
            if result.returncode != 0:
                return Response({
                    "success": False,
                    "error": result.stderr or "安装失败"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            skill_basename = skill_name.split('/')[-1].split('@')[0]
            installed_path = AGENT_SKILL_DIR / skill_basename
            
            return Response({
                "success": True,
                "data": {
                    "skill_name": skill_name,
                    "skill_basename": skill_basename,
                    "installed_path": str(installed_path),
                    "source": "user_installed",
                    "message": f"Skill {skill_name} 安装成功"
                }
            })
            
        except subprocess.TimeoutExpired:
            return Response({
                "success": False,
                "error": "安装超时，请稍后重试"
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except Exception as e:
            logger.error(f"Install skill error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SkillExecuteView(APIView):
    """执行技能（AI 生成内容）"""
    permission_classes = [IsAuthenticated]
    
    async def post(self, request: Request) -> Response:
        from core.services.chatbot_execution_logger import get_chatbot_logger
        
        skill_name = request.data.get('skill_name')
        user_input = request.data.get('user_input')
        provider = request.data.get('provider', 'qwen')
        
        if not skill_name:
            return Response({
                "success": False,
                "error": "请提供 skill_name"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_input:
            return Response({
                "success": False,
                "error": "请提供 user_input"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        conversation_id = request.data.get('conversation_id', 'manual-skill-exec')
        logger_exec = get_chatbot_logger(conversation_id)
        logger_exec.start('skill', f'执行Skill: {skill_name}', f'正在执行 Skill "{skill_name}"')
        
        start_time = time.time()
        
        skill_path = None
        skill_source = None
        
        for skill_dir in [SKILL_DIR, AGENT_SKILL_DIR]:
            candidate_path = skill_dir / skill_name / "SKILL.md"
            if candidate_path.exists():
                skill_path = candidate_path
                skill_source = 'builtin' if skill_dir == SKILL_DIR else 'user_installed'
                break
        
        if not skill_path:
            return Response({
                "success": False,
                "error": f"Skill {skill_name} not found in builtin or user_installed skills"
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            if not skill_path.resolve().is_relative_to(SKILL_DIR.resolve()) and \
               not skill_path.resolve().is_relative_to(AGENT_SKILL_DIR.resolve()):
                return Response({
                    "success": False,
                    "error": "Invalid skill name"
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, RuntimeError):
            return Response({
                "success": False,
                "error": "Invalid skill name"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            skill_content = skill_path.read_text(encoding='utf-8')
            
            system_prompt = f"""你是一个专业的AI助手，现在需要根据以下技能指导来完成任务。

## 技能指导文档

{skill_content}

---

## 用户需求

{user_input}

---

请根据技能指导文档的要求和最佳实践，完成用户的任务。确保输出内容符合技能文档中定义的标准和格式。
"""
            
            llm_service = create_llm_service(provider=provider)
            
            response = await llm_service.generate(
                prompt=user_input,
                system_message=system_prompt,
                temperature=0.7,
                max_tokens=4096
            )
            
            execution_time = time.time() - start_time
            
            result_text = response.get("text", "") if isinstance(response, dict) else str(response)  # type: ignore[unreachable]
            
            logger_exec.finish({
                'status': 'success',
                'skill_name': skill_name,
                'execution_time': round(execution_time, 2)
            })
            
            return Response({
                "success": True,
                "data": {
                    "skill_name": skill_name,
                    "user_input": user_input,
                    "result": result_text,
                    "execution_time": round(execution_time, 2),
                    "provider": provider
                },
                "execution_log_ids": logger_exec.get_log_ids()
            })
            
        except Exception as e:
            logger_exec.finish({
                'status': 'error',
                'error': str(e)
            })
            logger.error(f"Execute skill error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e),
                "execution_log_ids": logger_exec.get_log_ids()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)