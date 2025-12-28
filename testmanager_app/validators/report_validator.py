"""
报告参数验证器
提供报告生成的参数验证功能

⚠️ DEPRECATED: 此验证器已废弃
建议使用 GenerateReportSerializer 替代
"""

import warnings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
from testmanager_app.models import Project


class ReportValidator:
    """
    报告生成参数验证器

    统一验证报告生成的所有参数，提供清晰的错误信息
    """

    @staticmethod
    def validate_generate_report_params(data):
        """
        验证生成报告参数

        ⚠️ DEPRECATED: 此方法已废弃，建议使用 GenerateReportSerializer.validate() 替代

        Args:
            data: 请求数据字典，包含project_id, start_date, end_date

        Returns:
            tuple: (project, start_date, end_date) 验证后的对象

        Raises:
            ValidationError: 验证失败时抛出，包含所有错误信息
        """
        warnings.warn(
            "ReportValidator.validate_generate_report_params() is deprecated. "
            "Use GenerateReportSerializer instead.",
            DeprecationWarning,
            stacklevel=2
        )
        project_id = data.get('project_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')

        # 收集所有错误
        errors = []

        # 1. 基本验证 - 检查必需字段
        if not project_id:
            errors.append('project_id is required')

        if not start_date_str:
            errors.append('start_date is required')

        if not end_date_str:
            errors.append('end_date is required')

        # 如果有基本字段缺失，先返回错误
        if errors:
            raise ValidationError({'errors': errors})

        # 2. 类型验证和转换
        # 验证project_id并获取Project对象
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            raise ValidationError({'errors': [f'Project with id {project_id} not found']})
        except (ValueError, TypeError):
            raise ValidationError({'errors': [f'Invalid project_id: {project_id}']})

        # 验证并转换日期
        try:
            start_date = ReportValidator._parse_datetime(start_date_str)
            end_date = ReportValidator._parse_datetime(end_date_str)
        except ValueError as e:
            raise ValidationError({'errors': [f'Invalid date format: {str(e)}']})

        # 3. 业务逻辑验证
        # 验证日期范围合理性
        if start_date > end_date:
            raise ValidationError({'errors': ['Start date cannot be later than end date']})

        # 验证日期不能超过当前时间
        now = timezone.now()
        if end_date > now:
            raise ValidationError({'errors': ['End date cannot be in the future']})

        # 验证日期范围不能过大（例如不能超过1年）
        max_range = timezone.timedelta(days=365)
        if end_date - start_date > max_range:
            raise ValidationError({'errors': ['Date range cannot exceed 1 year']})

        return project, start_date, end_date

    @staticmethod
    def _parse_datetime(date_str):
        """
        解析日期时间字符串

        Args:
            date_str: ISO 8601格式的日期字符串

        Returns:
            datetime: 解析后的datetime对象

        Raises:
            ValueError: 解析失败时抛出
        """
        # 处理前端可能发送的Z结尾的UTC时间格式
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')

        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f'Invalid date format: {date_str}. Expected ISO 8601 format')
