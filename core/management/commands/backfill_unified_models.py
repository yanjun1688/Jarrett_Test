"""
Management command to backfill existing scripts and execution records
into the UnifiedScript and UnifiedExecution bridge models.

Usage:
    python manage.py backfill_unified_models
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from core.models.unified import (
    ScriptType,
    UnifiedExecution,
    UnifiedScript,
    UnifiedStatus,
)
from core.signals import (
    EXECUTION_SENDER_CONFIG,
    STATUS_MAP,
    _get_completed_at,
    _get_duration_seconds,
    _get_error_message,
    _get_executor,
)

logger = logging.getLogger(__name__)


SCRIPT_SOURCE_MODELS: List[tuple[str, str, str]] = [
    ('testmanager_app', 'TestScript', ScriptType.API),
    ('test_ui_app', 'UITestScript', ScriptType.UI),
    ('testmanager_app', 'PressureTestConfig', ScriptType.PRESSURE),
    ('testmanager_app', 'AdvancedPressureTestConfig', ScriptType.ADVANCED_PRESSURE),
]

EXECUTION_SOURCE_MODELS: List[tuple[str, str]] = [
    ('testmanager_app', 'ScriptExecution'),
    ('test_ui_app', 'UITestExecution'),
    ('testmanager_app', 'PressureTestExecution'),
    ('testmanager_app', 'AdvancedPressureTestExecution'),
]


class Command(BaseCommand):
    help = '回填现有脚本和执行记录到统一桥接模型'

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING('开始回填统一模型...'))
        self._backfill_scripts()
        self._backfill_executions()
        self.stdout.write(self.style.SUCCESS('回填完成!'))

    def _backfill_scripts(self) -> None:
        """回填脚本到 UnifiedScript"""
        self.stdout.write('\n--- 回填脚本 ---')
        from django.apps import apps

        for app_label, model_name, script_type in SCRIPT_SOURCE_MODELS:
            try:
                model_class = apps.get_model(app_label, model_name)
            except LookupError:
                self.stdout.write(self.style.WARNING(
                    f'  {model_name}: 模型不存在，跳过'
                ))
                continue

            ct = ContentType.objects.get_for_model(model_class)
            existing_ids = set(
                UnifiedScript.objects.filter(content_type=ct)
                .values_list('object_id', flat=True)
            )

            to_create: List[UnifiedScript] = []
            for obj in model_class.objects.select_related('project', 'created_by').iterator():
                if obj.pk not in existing_ids:
                    to_create.append(UnifiedScript(
                        name=obj.name,
                        description=obj.description,
                        script_type=script_type,
                        project=obj.project,
                        created_by=obj.created_by,
                        is_active=getattr(obj, 'is_active', True),
                        content_type=ct,
                        object_id=obj.pk,
                    ))

            if to_create:
                UnifiedScript.objects.bulk_create(to_create, ignore_conflicts=True)

            self.stdout.write(
                f'  {model_name}: 创建 {len(to_create)}, 已存在 {len(existing_ids)}'
            )

    def _backfill_executions(self) -> None:
        """回填执行记录到 UnifiedExecution"""
        self.stdout.write('\n--- 回填执行记录 ---')
        from django.apps import apps

        for app_label, model_name in EXECUTION_SOURCE_MODELS:
            try:
                model_class = apps.get_model(app_label, model_name)
            except LookupError:
                self.stdout.write(self.style.WARNING(
                    f'  {model_name}: 模型不存在，跳过'
                ))
                continue

            exec_ct = ContentType.objects.get_for_model(model_class)
            existing_ids = set(
                UnifiedExecution.objects.filter(content_type=exec_ct)
                .values_list('object_id', flat=True)
            )

            # Get the FK attr and script model for this execution type
            fk_attr: Optional[str] = None
            script_model: Optional[Type[Any]] = None
            for sender, (attr, s_model) in EXECUTION_SENDER_CONFIG.items():
                if sender.__name__ == model_name:
                    fk_attr = attr
                    script_model = s_model
                    break

            if fk_attr is None or script_model is None:
                self.stdout.write(self.style.WARNING(
                    f'  {model_name}: 未找到执行配置，跳过'
                ))
                continue

            script_ct = ContentType.objects.get_for_model(script_model)
            status_map: Dict[str, str] = STATUS_MAP.get(model_name, {})

            # Build a lookup of source script pk -> UnifiedScript
            unified_script_map: Dict[int, UnifiedScript] = {}
            for us in UnifiedScript.objects.filter(content_type=script_ct):
                unified_script_map[us.object_id] = us

            to_create: List[UnifiedExecution] = []
            skipped = 0
            for obj in model_class.objects.select_related(fk_attr).iterator():
                if obj.pk in existing_ids:
                    continue

                source_script = getattr(obj, fk_attr)
                unified_script = unified_script_map.get(source_script.pk)
                if unified_script is None:
                    skipped += 1
                    continue

                unified_status = status_map.get(obj.status, UnifiedStatus.PENDING)

                to_create.append(UnifiedExecution(
                    unified_script=unified_script,
                    status=unified_status,
                    executed_by=_get_executor(model_class, obj),
                    started_at=obj.started_at,
                    completed_at=_get_completed_at(model_class, obj),
                    duration_seconds=_get_duration_seconds(model_class, obj),
                    error_message=_get_error_message(model_class, obj),
                    content_type=exec_ct,
                    object_id=obj.pk,
                ))

            if to_create:
                UnifiedExecution.objects.bulk_create(to_create, ignore_conflicts=True)

            msg = f'  {model_name}: 创建 {len(to_create)}, 已存在 {len(existing_ids)}'
            if skipped:
                msg += f', 跳过(无对应脚本) {skipped}'
            self.stdout.write(msg)
