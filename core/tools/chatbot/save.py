"""
通用 Save 工具
根据 scenario 的 save_config 配置，动态加载 serializer 并保存数据到数据库。
"""
from __future__ import annotations

import importlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from core.tools.base_tool import BaseTool, ToolResult
from core.schemas.scenarios import SCENARIOS, FIELD_MAPPING_KEY_SELF, FIELD_MAPPING_KEY_NONE

logger = logging.getLogger(__name__)

_SAVE_KWARG_DEFAULTS: Dict[str, Any] = {"source": "chatbot"}


def _save_item(
    serializer_class: Any,
    ser_data: Dict[str, Any],
    created_by_field: Optional[str],
    user_id: Any,
    save_kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    serializer = serializer_class(data=ser_data)
    serializer.is_valid(raise_exception=True)
    extra_kwargs: Dict[str, Any] = dict(save_kwargs or {})
    if created_by_field and user_id:
        extra_kwargs[created_by_field] = user_id
    return serializer.save(**extra_kwargs)


class SaveTool(BaseTool):
    """根据 scenario 配置将生成的 JSON 内容保存到数据库"""

    def __init__(self) -> None:
        super().__init__(
            name="save",
            description="将 generate 工具返回的 JSON 内容保存到数据库。根据 scenario 决定保存方式和目标表。",
            version="2.0.0",
        )

    def _build_parameters_schema(self) -> Dict[str, Any]:
        return {
            "scenario": {
                "type": "string",
                "description": "保存场景（和 generate 的 scenario 对应）",
                "enum": list(SCENARIOS.keys()),
            },
            "output": {
                "type": "string",
                "description": "要保存的内容（JSON 格式，由 generate 工具返回）",
            },
            "project_id": {
                "type": "integer",
                "description": "目标项目 ID",
            },
            "name": {
                "type": "string",
                "description": "名称（可选，用于脚本名称等）",
            },
            "source": {
                "type": "string",
                "enum": ["chatbot", "manual_upload", "manual_create"],
                "description": "来源标识",
                "default": "chatbot",
            },
        }

    def _get_required_parameters(self) -> List[str]:
        return ["scenario", "output", "project_id"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        scenario = kwargs.get("scenario")
        output = kwargs.get("output")
        project_id = kwargs.get("project_id")
        name = kwargs.get("name")
        # user_id 由 ReAct 引擎或 agent 注入，不通过参数 schema 暴露给 LLM
        user_id = kwargs.get("user_id")

        if not scenario or not output or not project_id:
            missing = []
            if not scenario:
                missing.append("scenario")
            if not output:
                missing.append("output")
            if not project_id:
                missing.append("project_id")
            return ToolResult(
                success=False,
                data={},
                error=f"缺少必填参数: {', '.join(missing)}",
            )

        config = SCENARIOS.get(scenario)
        if not config:
            return ToolResult(
                success=False,
                data={},
                error=f"未知场景: {scenario}。可用场景: {', '.join(SCENARIOS.keys())}",
            )

        save_config = config.get("save_config")
        if not save_config:
            return ToolResult(
                success=False,
                data={},
                error=f"场景 '{scenario}' 未配置保存",
            )

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                data={},
                error=f"JSON 格式错误: {e}。请重新生成。",
            )

        validate_fn = config.get("validate")
        if validate_fn:
            is_valid, error_msg = validate_fn(data)
            if not is_valid:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"格式错误: {error_msg}。请参考参数说明重试。",
                )

        try:
            module = importlib.import_module(save_config["serializer_module"])
            serializer_class = getattr(module, save_config["serializer"])
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load serializer for scenario '{scenario}': {e}")
            return ToolResult(
                success=False,
                data={},
                error=f"内部错误: 无法加载序列化器 ({save_config['serializer']})",
            )

        root_key = save_config.get("root_key")
        if root_key:
            items = data.get(root_key, [])
            if not isinstance(items, list):
                items = [items]
        else:
            items = [data]

        auto_fields = dict(save_config.get("auto_fields", {}))
        now = datetime.now()
        resolved_auto: Dict[str, Any] = {}
        for field, template in auto_fields.items():
            value = template.replace("{timestamp}", now.strftime("%Y%m%d%H%M%S"))
            if field == "name" and name:
                value = name
            resolved_auto[field] = value

        field_mapping = save_config.get("field_mapping", {})
        project_field = save_config.get("project_field")
        created_by_field = save_config.get("created_by_field")

        raw_save_kwargs = save_config.get("save_kwargs", {})
        resolved_save_kwargs: Dict[str, Any] = {}
        for k, v in raw_save_kwargs.items():
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                param_name = v[1:-1]
                resolved_save_kwargs[k] = kwargs.get(param_name, _SAVE_KWARG_DEFAULTS.get(param_name))
            else:
                resolved_save_kwargs[k] = v

        saved_ids: List[str] = []

        def _save_all() -> List[str]:
            ids: List[str] = []
            with transaction.atomic():
                for item in items:
                    serializer_data: Dict[str, Any] = {}
                    for db_field, json_field in field_mapping.items():
                        if json_field == FIELD_MAPPING_KEY_SELF:
                            serializer_data[db_field] = json.dumps(item, ensure_ascii=False)
                        elif json_field == FIELD_MAPPING_KEY_NONE:
                            continue
                        else:
                            value = item.get(json_field, "")
                            serializer_data[db_field] = value
                    serializer_data.update(resolved_auto)
                    if project_field:
                        serializer_data[project_field] = project_id
                    obj = _save_item(
                        serializer_class, serializer_data,
                        created_by_field, user_id, resolved_save_kwargs,
                    )
                    ids.append(str(getattr(obj, "id", getattr(obj, "pk", ""))))
            return ids

        saved_ids = await sync_to_async(_save_all)()

        return ToolResult(
            success=True,
            data={
                "saved_count": len(saved_ids),
                "ids": saved_ids,
                "message": f"成功保存 {len(saved_ids)} 条记录",
            },
            metadata={"scenario": scenario, "project_id": project_id},
        )
