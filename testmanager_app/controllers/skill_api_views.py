"""
Skill API 视图 — MCP Server 代理版本

通过 MCP Skill Manager Server 统一处理搜索、安装、列表请求。
旧版直接调用 npx CLI 的视图已删除。
"""
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import json
import logging

logger = logging.getLogger(__name__)

class SkillSearchMCPView(APIView):
    """
    搜索远程 Skills - MCP Server 代理版本

    替代已废弃的 SkillRemoteSearchView
    通过 MCP Skill Manager Server 统一处理搜索请求
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        keyword = request.data.get('keyword', '').strip()

        if not keyword:
            return Response({
                "success": False,
                "error": "请输入搜索关键词"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from core.agents.capability.mcp_lifespan import global_mcp_manager
            from asgiref.sync import async_to_sync

            # 使用 async_to_sync 在同步上下文中调用异步 MCP 方法
            result = async_to_sync(global_mcp_manager.call_tool)(
                "skill-manager",
                "search_skills",
                {"keyword": keyword}
            )

            # result 是 MCP Server 返回的内容列表
            if isinstance(result, list) and len(result) > 0:
                content = result[0]
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                else:
                    data = content
            elif isinstance(result, dict):
                data = result
            else:
                data = {"success": False, "error": "Invalid response format", "skills": []}

            return Response(data)

        except Exception as e:
            logger.error(f"[SkillSearchMCPView] 搜索失败: {e}", exc_info=True)
            return Response({
                "success": False,
                "error": f"搜索失败: {str(e)}",
                "output": ""
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SkillInstallMCPView(APIView):
    """
    安装远程 Skill - MCP Server 代理版本

    替代已废弃的 SkillInstallView
    通过 MCP Skill Manager Server 统一处理安装请求
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        skill_id = request.data.get('skill_id') or request.data.get('skill_name')
        skill_name = request.data.get('skill_name_alias')  # 可选的安装后名称

        if not skill_id:
            return Response({
                "success": False,
                "error": "请提供 skill_id"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from core.agents.capability.mcp_lifespan import global_mcp_manager
            from asgiref.sync import async_to_sync

            # 使用 async_to_sync 在同步上下文中调用异步 MCP 方法
            result = async_to_sync(global_mcp_manager.call_tool)(
                "skill-manager",
                "install_skill",
                {"skill_id": skill_id, "skill_name": skill_name}
            )

            # 解析 MCP 返回结果
            if isinstance(result, list) and len(result) > 0:
                content = result[0]
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                else:
                    data = content
            elif isinstance(result, dict):
                data = result
            else:
                data = {"success": False, "error": "Invalid response format"}

            if data.get("success"):
                return Response({
                    "success": True,
                    "data": data
                })
            else:
                return Response({
                    "success": False,
                    "error": data.get("error", "安装失败")
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"[SkillInstallMCPView] 安装失败: {e}", exc_info=True)
            return Response({
                "success": False,
                "error": f"安装失败: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SkillListMCPView(APIView):
    """
    获取本地 Skills 列表 - MCP Server 代理版本

    替代 SkillLocalListView 的同步版本
    通过 MCP Skill Manager Server 统一获取列表
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            from core.agents.capability.mcp_lifespan import global_mcp_manager
            from asgiref.sync import async_to_sync

            # 使用 async_to_sync 在同步上下文中调用异步 MCP 方法
            result = async_to_sync(global_mcp_manager.call_tool)(
                "skill-manager",
                "list_local_skills",
                {}
            )

            # 解析 MCP 返回结果
            if isinstance(result, list) and len(result) > 0:
                content = result[0]
                if hasattr(content, 'text'):
                    data = json.loads(content.text)
                else:
                    data = content
            elif isinstance(result, dict):
                data = result
            else:
                data = {"success": False, "error": "Invalid response format", "skills": []}

            return Response(data)

        except Exception as e:
            logger.error(f"[SkillListMCPView] 获取列表失败: {e}", exc_info=True)
            return Response({
                "success": False,
                "error": f"获取列表失败: {str(e)}",
                "skills": []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)