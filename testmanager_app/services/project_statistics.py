"""
项目统计服务
提供项目相关的统计计算功能
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from django.db.models import Count, Q
from core.models import Project, TestCase, TestExecution


def get_project_statistics(project_id: int) -> Optional[Dict[str, Any]]:
    """
    获取项目统计信息（包含功能测试和API测试）

    使用统一的自定义 QuerySet 方法，确保统计逻辑一致性

    Args:
        project_id: 项目ID

    Returns:
        dict: 项目统计信息，包含测试用例数、执行记录、通过率等
        如果项目不存在，返回None
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return None

    # 统计功能测试用例
    total_testcases = TestCase.objects.filter(project=project).count()

    # 使用自定义 QuerySet 方法统一聚合统计
    stats = TestExecution.objects.by_project(project).aggregate_stats()  # type: ignore[attr-defined]

    # 提取统计数据
    total_executions = stats.get('total_executions', 0)
    passed_executions = stats.get('passed_executions', 0)
    failed_executions = stats.get('failed_executions', 0)
    blocked_executions = stats.get('blocked_executions', 0)
    skipped_executions = stats.get('skipped_executions', 0)

    # 计算通过率
    pass_rate = round((passed_executions / total_executions * 100), 2) if total_executions > 0 else 0

    # 按测试类型细分统计
    testcase_executions = TestExecution.objects.filter(
        test_type='testcase',
        test_case__project=project
    )
    testcase_stats = testcase_executions.aggregate(
        total=Count('id'),
        passed=Count('id', filter=Q(status='passed')),
        failed=Count('id', filter=Q(status='failed')),
        blocked=Count('id', filter=Q(status='blocked')),
        skipped=Count('id', filter=Q(status='skipped')),
    )

    api_executions = TestExecution.objects.filter(
        test_type='api',
        api_request__project=project
    )
    api_stats = api_executions.aggregate(
        total=Count('id'),
        passed=Count('id', filter=Q(status='passed')),
        failed=Count('id', filter=Q(status='failed')),
        blocked=Count('id', filter=Q(status='blocked')),
        skipped=Count('id', filter=Q(status='skipped')),
    )

    data: Dict[str, Any] = {
        'project_id': project.id,
        'project_name': project.name,
        'total_testcases': total_testcases,
        'total_executions': total_executions,
        'passed_executions': passed_executions,
        'failed_executions': failed_executions,
        'blocked_executions': blocked_executions,
        'skipped_executions': skipped_executions,
        'pass_rate': pass_rate,
        'detail': {
            'testcase': {
                'total': testcase_stats.get('total', 0),
                'passed': testcase_stats.get('passed', 0),
                'failed': testcase_stats.get('failed', 0),
                'blocked': testcase_stats.get('blocked', 0),
                'skipped': testcase_stats.get('skipped', 0),
            },
            'api': {
                'total': api_stats.get('total', 0),
                'passed': api_stats.get('passed', 0),
                'failed': api_stats.get('failed', 0),
                'blocked': api_stats.get('blocked', 0),
                'skipped': api_stats.get('skipped', 0),
            }
        }
    }
    
    return data
