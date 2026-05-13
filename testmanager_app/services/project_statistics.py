"""
项目统计服务
提供项目相关的统计计算功能
"""
# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from django.db.models import Count, Q
from django.core.cache import cache
from core.models import Project, TestExecution
from core.models.knowledge import KnowledgeBase, KnowledgeDocument
from testmanager_app.models import FeatureTestCase, TestScript
from testmanager_app.utils.cache_helper import (
    get_cache_key,
    CACHE_KEY_PREFIX,
)

logger = logging.getLogger(__name__)


def _get_global_stats() -> Dict[str, Any]:
    """内部函数: 全局聚合统计（带缓存）"""
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], 'all')
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    stats = TestExecution.objects.all().aggregate_stats()  # type: ignore[attr-defined]

    data = {
        'total_projects': Project.objects.count(),
        'active_projects': Project.objects.filter(is_active=True).count(),
        'total_testcases': FeatureTestCase.objects.count(),
        'total_scripts': TestScript.objects.count(),
        'total_knowledge_bases': KnowledgeBase.objects.count(),
        'total_documents': KnowledgeDocument.objects.count(),
        'total_executions': stats.get('total_executions', 0),
        'passed_executions': stats.get('passed_executions', 0),
        'failed_executions': stats.get('failed_executions', 0),
        'blocked_executions': stats.get('blocked_executions', 0),
        'skipped_executions': stats.get('skipped_executions', 0),
        'pass_rate': round(
            (stats.get('passed_executions', 0) / stats.get('total_executions', 0) * 100), 2
        ) if stats.get('total_executions', 0) > 0 else 0,
    }
    cache.set(cache_key, data, 300)
    return data


def _get_project_stats(project: Project) -> Dict[str, Any]:
    """内部函数: 单项目统计（带缓存）"""
    cache_key = get_cache_key(CACHE_KEY_PREFIX['project_stats'], project.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    total_tc = FeatureTestCase.objects.filter(project=project).count()
    es = TestExecution.objects.by_project(project).aggregate_stats()  # type: ignore[attr-defined]
    total_exec = es.get('total_executions', 0)
    passed = es.get('passed_executions', 0)

    def _type_agg(test_type: str, fk: str) -> Dict[str, int]:
        return TestExecution.objects.filter(test_type=test_type, **{fk: project}).aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(status='passed')),
            failed=Count('id', filter=Q(status='failed')),
            blocked=Count('id', filter=Q(status='blocked')),
            skipped=Count('id', filter=Q(status='skipped')),
        )

    data = {
        'project_id': project.id,
        'project_name': project.name,
        'total_testcases': total_tc,
        'total_scripts': TestScript.objects.filter(project=project).count(),
        'total_knowledge_bases': KnowledgeBase.objects.filter(project=project).count(),
        'total_documents': KnowledgeDocument.objects.filter(knowledge_base__project=project).count(),
        'total_executions': total_exec,
        'passed_executions': passed,
        'failed_executions': es.get('failed_executions', 0),
        'blocked_executions': es.get('blocked_executions', 0),
        'skipped_executions': es.get('skipped_executions', 0),
        'pass_rate': round((passed / total_exec * 100), 2) if total_exec > 0 else 0,
        'detail': {
            'feature': {'total': total_tc, 'passed': 0, 'failed': 0, 'blocked': 0, 'skipped': 0},
            'api': _type_agg('api', 'api_request__project'),
            'script': _type_agg('script', 'test_script__project'),
        },
    }
    cache.set(cache_key, data, 300)
    return data


def get_statistics(project_id: Optional[int] = None) -> Dict[str, Any]:
    """统一统计接口

    - project_id=None → 所有项目
    - project_id=N    → 指定项目
    """
    global_stats = _get_global_stats()
    if project_id is not None:
        project = Project.objects.get(id=project_id)
        projects = [_get_project_stats(project)]
    else:
        projects = [_get_project_stats(p) for p in Project.objects.all()]
    return {'global': global_stats, 'projects': projects}
