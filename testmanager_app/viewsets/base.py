"""
Base ViewSets and Mixins for testmanager_app
优化代码重复问题，提供通用功能
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from django.db.models import QuerySet

from rest_framework import viewsets
from testmanager_app.permissions import IsSuperUser


class BaseViewSet(viewsets.ModelViewSet):
    """
    基础ViewSet，统一定义权限和数据创建逻辑

    特性：
    - 自动设置 permission_classes = [IsSuperUser]
    - 自动填充 created_by / executor 字段
    """
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        """
        自动保存创建者

        支持字段名：
        - created_by: 常规创建者字段
        - executor: 执行者字段（用于执行记录）
        """
        user = self.request.user if self.request.user.is_authenticated else None

        Model = getattr(serializer.Meta, 'model', None)
        if Model:
            if hasattr(Model, 'executor'):
                serializer.save(executor=user)
            elif hasattr(Model, 'created_by'):
                serializer.save(created_by=user)
            else:
                serializer.save()
        else:
            try:
                serializer.save(created_by=user)
            except Exception:
                serializer.save()


class QueryOptimizerMixin:
    """
    自动优化查询性能的Mixin

    通过在ViewSet中声明 select_related_fields 和 prefetch_related_fields，
    自动应用查询优化，避免N+1查询问题。

    示例：
        class MyViewSet(QueryOptimizerMixin, BaseViewSet):
            queryset = MyModel.objects.all()
            select_related_fields = ['project', 'module', 'created_by']
            prefetch_related_fields = ['tags', 'comments']
    """

    select_related_fields: List[str] = []
    prefetch_related_fields: List[str] = []

    def get_queryset(self) -> QuerySet:
        """
        自动应用查询优化

        继承类无需重写此方法，只需声明上面的字段列表即可
        """
        queryset: QuerySet = super().get_queryset()  # type: ignore[misc]

        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)

        if self.prefetch_related_fields:
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset


class CommonFilterMixin:
    """
    通用过滤逻辑Mixin，自动处理常见查询参数

    通过在ViewSet中声明过滤器配置，自动处理查询参数，
    避免在get_queryset中重复编写过滤逻辑。

    支持的过滤类型：
    - filter_int_fields: 整数字段精确匹配（?project=1&module=2）
    - filter_str_fields: 字符串段精确匹配（?name=test）
    - filter_choice_fields: 选项段精确匹配（?status=pending）
    - filter_bool_fields: 布尔段匹配（?is_active=true）
    - filter_related_icontains: 关联模型字段的模糊搜索（?project__name__icontains=xxx）
    - filter_date_range: 日期范围过滤（?date_from=2024-01-01&date_to=2024-12-31）
    """

    filter_int_fields: List[str] = []
    filter_str_fields: List[str] = []
    filter_choice_fields: Dict[str, List[str]] = {}
    filter_bool_fields: List[str] = []
    filter_related_icontains: List[str] = []
    filter_date_range: List[str] = []

    def get_queryset(self) -> QuerySet:
        """
        自动应用所有配置的过滤器

        子类可以重写此方法来添加自定义过滤逻辑，
        但要记得调用 super().get_queryset() 来应用这里的通用过滤器
        """
        queryset: QuerySet = super().get_queryset()  # type: ignore[misc]

        for field in self.filter_int_fields:
            value = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if value:
                try:
                    queryset = queryset.filter(**{field: int(value)})
                except (ValueError, TypeError):
                    pass

        for field in self.filter_str_fields:
            value = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if value:
                queryset = queryset.filter(**{field: value})

        for field, choices in self.filter_choice_fields.items():
            value = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if value and value in choices:
                queryset = queryset.filter(**{field: value})

        for field in self.filter_bool_fields:
            value = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if value:
                queryset = queryset.filter(**{field: value.lower() == 'true'})

        for field in self.filter_related_icontains:
            value = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if value:
                queryset = queryset.filter(**{f"{field}__icontains": value})

        for field in self.filter_date_range:
            from_param = f"{field}_from"
            to_param = f"{field}_to"
            from_value = self.request.query_params.get(from_param)  # type: ignore[attr-defined]
            to_value = self.request.query_params.get(to_param)  # type: ignore[attr-defined]

            if from_value or to_value:
                filter_dict = {}
                if from_value:
                    filter_dict[f"{field}__gte"] = from_value
                if to_value:
                    filter_dict[f"{field}__lte"] = to_value
                if filter_dict:
                    queryset = queryset.filter(**filter_dict)

        return queryset