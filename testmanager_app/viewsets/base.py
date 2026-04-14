"""
Base ViewSets and Mixins for testmanager_app
优化代码重复问题，提供通用功能
"""

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
        # 获取用户（未认证则为None）
        user = self.request.user if self.request.user.is_authenticated else None

        # 检查serializer的Meta.model有哪些字段
        Model = getattr(serializer.Meta, 'model', None)
        if Model:
            # 如果模型有executor字段，优先使用（执行记录类）
            if hasattr(Model, 'executor'):
                serializer.save(executor=user)
            # 如果模型有created_by字段，使用它
            elif hasattr(Model, 'created_by'):
                serializer.save(created_by=user)
            else:
                # 默认调用父类方法
                serializer.save()
        else:
            # 如果无法获取模型，尝试保存 created_by
            try:
                serializer.save(created_by=user)
            except Exception:
                # 如果失败，不设置创建者
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

    # 需要select_related的字段列表
    select_related_fields = []

    # 需要prefetch_related的字段列表
    prefetch_related_fields = []

    def get_queryset(self):
        """
        自动应用查询优化

        继承类无需重写此方法，只需声明上面的字段列表即可
        """
        # 从父类获取queryset
        queryset = super().get_queryset()

        # 自动应用select_related优化
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)

        # 自动应用prefetch_related优化
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

    # 整数段过滤器配置（字段名列表）
    filter_int_fields = []

    # 字符串字段过滤器配置（字段名列表）
    filter_str_fields = []

    # 选项字段过滤器配置（字段名: 可选值列表）
    filter_choice_fields = {}

    # 布尔字段过滤器配置（字段名列表）
    filter_bool_fields = []

    # 关联模型字段的模糊搜索配置（字段名列表，如 'project__name'）
    filter_related_icontains = []

    # 日期范围过滤器配置（字段名列表）
    filter_date_range = []

    def get_queryset(self):
        """
        自动应用所有配置的过滤器

        子类可以重写此方法来添加自定义过滤逻辑，
        但要记得调用 super().get_queryset() 来应用这里的通用过滤器
        """
        queryset = super().get_queryset()

        # 整数段精确匹配
        for field in self.filter_int_fields:
            value = self.request.query_params.get(field)
            if value:
                try:
                    queryset = queryset.filter(**{field: int(value)})
                except (ValueError, TypeError):
                    pass

        # 字符串字段精确匹配
        for field in self.filter_str_fields:
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})

        # 选项字段精确匹配
        for field, choices in self.filter_choice_fields.items():
            value = self.request.query_params.get(field)
            if value and value in choices:
                queryset = queryset.filter(**{field: value})

        # 布尔字段匹配
        for field in self.filter_bool_fields:
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value.lower() == 'true'})

        # 关联模型字段的模糊搜索（icontains）
        for field in self.filter_related_icontains:
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{f"{field}__icontains": value})

        # 日期范围过滤
        for field in self.filter_date_range:
            from_param = f"{field}_from"
            to_param = f"{field}_to"
            from_value = self.request.query_params.get(from_param)
            to_value = self.request.query_params.get(to_param)

            if from_value or to_value:
                filter_dict = {}
                if from_value:
                    filter_dict[f"{field}__gte"] = from_value
                if to_value:
                    filter_dict[f"{field}__lte"] = to_value
                if filter_dict:
                    queryset = queryset.filter(**filter_dict)

        return queryset
