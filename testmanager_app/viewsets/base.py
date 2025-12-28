"""
Base ViewSets and Mixins for testmanager_app
优化代码重复问题，提供通用功能
"""

from rest_framework import viewsets
from testmanager_app.permissions import RoleBasedPermission


class BaseViewSet(viewsets.ModelViewSet):
    """
    基础ViewSet，统一定义权限和数据创建逻辑

    特性：
    - 自动设置 permission_classes = [RoleBasedPermission]
    - 自动填充 created_by / executor 字段
    """
    permission_classes = [RoleBasedPermission]

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
            except:
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
        # 从父类或自身获取queryset
        queryset = super().get_queryset() if hasattr(super(), 'get_queryset') else self.queryset

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
    - filter_str_fields: 字符串包含查询（?name=xxx）
    - filter_choice_fields: 选项字段过滤（?status=pending）
    - filter_related_icontains: 关联字段模糊查询（?project__name__icontains=xxx）

    示例：
        class MyViewSet(CommonFilterMixin, QueryOptimizerMixin, BaseViewSet):
            queryset = MyModel.objects.all()

            filter_int_fields = ['project', 'module']
            filter_str_fields = ['name', 'description']
            filter_choice_fields = {'status': ['pending', 'passed', 'failed']}
            filter_related_icontains = ['project__name', 'module__name']
    """

    # 整数字段精确匹配（会从query_params获取并转换为int）
    filter_int_fields = []

    # 字符串字段包含查询（使用__icontains）
    filter_str_fields = []

    # 选项字段及可选值（字典：字段名 -> 可选值列表）
    filter_choice_fields = {}

    # 关联字段模糊查询（使用__icontains）
    filter_related_icontains = []

    def get_queryset(self):
        """
        应用通用过滤器

        会自动处理上述声明的过滤字段
        """
        # 先调用父类的get_queryset（可能是QueryOptimizerMixin）
        queryset = super().get_queryset() if hasattr(super(), 'get_queryset') else self.queryset

        # 导入工具函数
        from testmanager_app.viewsets.filters import safe_get_int_param, safe_get_str_param, safe_get_choice_param

        # 整数字段精确匹配（?project=1&module=2）
        for field in self.filter_int_fields:
            value = safe_get_int_param(self.request, field)
            if value is not None:
                queryset = queryset.filter(**{field: value})

        # 字符串字段包含查询（?name=xxx&description=yyy）
        for field in self.filter_str_fields:
            value = safe_get_str_param(self.request, field)
            if value is not None:
                queryset = queryset.filter(**{f"{field}__icontains": value})

        # 选项字段过滤（?status=pending）
        for field, choices in self.filter_choice_fields.items():
            value = safe_get_choice_param(self.request, field, choices)
            if value is not None:
                queryset = queryset.filter(**{field: value})

        # 关联字段模糊查询（?project__name__icontains=xxx）
        # query_params格式: project__name__icontains (双下划线)
        for field in self.filter_related_icontains:
            # 将 model字段格式(project__name) 转换为 query_params格式(project__name__icontains)
            query_param = f"{field}__icontains"
            value = safe_get_str_param(self.request, query_param)
            if value is not None:
                queryset = queryset.filter(**{f"{field}__icontains": value})

        return queryset
