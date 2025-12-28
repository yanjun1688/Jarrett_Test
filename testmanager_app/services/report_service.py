"""
测试报告服务
处理测试报告生成相关的业务逻辑
"""

import logging
from django.db import transaction
from django.db.models import Q, Count
from testmanager_app.models import TestExecution, TestReport

logger = logging.getLogger(__name__)


class ReportService:
    """
    测试报告生成服务

    处理报告生成的核心业务逻辑，包括数据聚合、报告创建等
    """

    @staticmethod
    @transaction.atomic
    def generate_report(project, start_date, end_date, created_by):
        """
        生成测试报告（带事务保护）

        Args:
            project: Project对象
            start_date: 开始时间
            end_date: 结束时间
            created_by: 创建者

        Returns:
            TestReport: 生成的报告实例

        Raises:
            Exception: 数据库操作失败时抛出
        """
        # 1. 获取执行统计数据
        stats = ReportService._get_execution_stats(project, start_date, end_date)

        # 2. 创建报告
        report = TestReport.objects.create(
            project=project,
            name=f"{project.name} 测试报告 {start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}",
            description=f"时间范围：{start_date.strftime('%Y-%m-%d %H:%M')} 至 {end_date.strftime('%Y-%m-%d %H:%M')}",
            start_date=start_date,
            end_date=end_date,
            total_cases=stats['total_cases'],
            passed_cases=stats['passed_cases'],
            failed_cases=stats['failed_cases'],
            blocked_cases=stats['blocked_cases'],
            skipped_cases=stats['skipped_cases'],
            created_by=created_by
        )

        logger.info(f"成功生成测试报告: report_id={report.id}, project={project.name}")

        return report

    @staticmethod
    def _get_execution_stats(project, start_date, end_date):
        """
        获取指定时间范围内的执行统计数据

        使用自定义 QuerySet 方法，简化查询逻辑，提高代码复用性

        Args:
            project: Project对象
            start_date: 开始时间
            end_date: 结束时间

        Returns:
            dict: 统计数据，包含total_cases, passed_cases, failed_cases, blocked_cases, skipped_cases

        Raises:
            Exception: 数据库查询失败时抛出
        """
        try:
            # 使用自定义 QuerySet 方法进行查询和聚合
            stats = TestExecution.objects.by_project_and_date_range(
                project, start_date, end_date
            ).aggregate_stats()

            # 处理NULL值，提供默认值0
            return {
                'total_cases': stats.get('total_cases', 0),
                'passed_cases': stats.get('passed_executions', 0),
                'failed_cases': stats.get('failed_executions', 0),
                'blocked_cases': stats.get('blocked_executions', 0),
                'skipped_cases': stats.get('skipped_executions', 0),
            }

        except Exception as e:
            logger.error(f"数据库聚合查询失败: {e}", exc_info=True)
            raise Exception(f"Failed to aggregate test execution data: {str(e)}")

    @staticmethod
    def get_report_list(project=None):
        """
        获取报告列表

        Args:
            project: 过滤的项目（可选）

        Returns:
            QuerySet: 报告查询集
        """
        queryset = TestReport.objects.all().order_by('-created_at')

        if project:
            queryset = queryset.filter(project=project)

        return queryset
