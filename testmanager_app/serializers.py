from rest_framework import serializers
from testmanager_app.models import Project, Module, TestCase, TestExecution, TestReport, TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection, CollectionExecution, FeatureTestCase, TestResult, Role, UserRole,CollectionRequest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class ModuleSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Module
        fields = '__all__'


class TestCaseSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TestCase
        fields = '__all__'


class TestCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['title', 'project', 'module', 'priority', 'precondition', 'steps', 'expected_result']


class TestExecutionSerializer(serializers.ModelSerializer):
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)
    api_request_name = serializers.CharField(source='api_request.name', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)

    class Meta:
        model = TestExecution
        fields = '__all__'


class TestExecutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestExecution
        fields = ['test_type', 'testcase', 'api_request', 'status', 'actual_result', 'comments', 'execution_duration', 'api_response_data', 'api_logs']


class TestExecutionListSerializer(serializers.ModelSerializer):
    """轻量级执行记录序列化器，用于列表展示，优化性能"""
    api_request_name = serializers.CharField(source='api_request.name', read_only=True)
    api_request_url = serializers.CharField(source='api_request.url', read_only=True)
    api_request_method = serializers.CharField(source='api_request.method', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    
    class Meta:
        model = TestExecution
        fields = [
            'id', 'test_type', 'api_request', 'api_request_name', 
            'api_request_url', 'api_request_method', 'status', 
            'actual_result', 'executed_at', 'executor_name'
        ]


class TestReportSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    pass_rate = serializers.ReadOnlyField()

    class Meta:
        model = TestReport
        fields = '__all__'


class GenerateReportSerializer(serializers.Serializer):
    """
    生成报告的参数验证器

    统一处理：
    - 字段存在性验证
    - 类型转换（project_id → Project对象，字符串 → datetime）
    - 业务规则验证（日期范围、未来日期等）
    """

    project_id = serializers.IntegerField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    def validate_project_id(self, value):
        """验证 project_id 并返回 Project 对象"""
        try:
            return Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError(f'Project with id {value} not found')

    def validate(self, data):
        """验证业务规则：日期范围合理性"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # 验证：开始日期不能晚于结束日期
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                'date_range': 'Start date cannot be later than end date'
            })

        # 验证：结束日期不能超过当前时间
        if end_date and end_date > timezone.now():
            raise serializers.ValidationError({
                'end_date': 'End date cannot be in the future'
            })

        # 验证：日期范围不能超过1年
        if start_date and end_date:
            max_range = timedelta(days=365)
            if end_date - start_date > max_range:
                raise serializers.ValidationError({
                    'date_range': 'Date range cannot exceed 1 year'
                })

        return data

    def to_representation(self, instance):
        """序列化输出（用于调试）"""
        return {
            'project_id': instance[0].id if instance else None,
            'start_date': instance[1].isoformat() if instance else None,
            'end_date': instance[2].isoformat() if instance else None,
        }


class TestScriptSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = TestScript
        fields = '__all__'
        read_only_fields = ['file']


class TestScriptCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestScript
        fields = ['id', 'name', 'description', 'script_type', 'project', 'file']
        read_only_fields = ['id']  # 创建后生成的ID，只读


class ScriptExecutionSerializer(serializers.ModelSerializer):
    script_name = serializers.CharField(source='script.name', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    
    class Meta:
        model = ScriptExecution
        fields = '__all__'


class ScriptExecutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScriptExecution
        fields = ['script']


class ApiRequestSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = ApiRequest
        fields = '__all__'


class ApiRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiRequest
        fields = ['name', 'description', 'url', 'method', 'headers', 'body', 'project']


class ApiAssertionSerializer(serializers.ModelSerializer):
    api_request_name = serializers.CharField(source='api_request.name', read_only=True)
    
    class Meta:
        model = ApiAssertion
        fields = '__all__'


class ApiAssertionCreateSerializer(serializers.ModelSerializer):
    """断言创建序列化器，包含字段路径的条件必填验证"""
    
    class Meta:
        model = ApiAssertion
        fields = ['api_request', 'assertion_type', 'field_path', 'comparison', 'expected_value']
    
    def validate(self, attrs):
        """验证字段路径的条件必填"""
        assertion_type = attrs.get('assertion_type')
        field_path = attrs.get('field_path', '').strip() if attrs.get('field_path') else ''
        
        # 当断言类型为响应体字段或响应头字段时，字段路径为必填
        if assertion_type in ['response_body_field', 'response_header_field']:
            if not field_path:
                raise serializers.ValidationError({
                    'field_path': f'当断言类型为"{dict(ApiAssertion.ASSERTION_TYPE_CHOICES).get(assertion_type, assertion_type)}"时，字段路径为必填项'
                })
        
        # 当断言类型为状态码或响应时间时，字段路径应为空
        if assertion_type in ['status_code', 'response_time']:
            if field_path:
                raise serializers.ValidationError({
                    'field_path': f'当断言类型为"{dict(ApiAssertion.ASSERTION_TYPE_CHOICES).get(assertion_type, assertion_type)}"时，不需要填写字段路径'
                })
        
        return attrs


class CollectionRequestSerializer(serializers.ModelSerializer):
    api_request_name = serializers.CharField(source='api_request.name', read_only=True)
    api_request_method = serializers.CharField(source='api_request.method', read_only=True)
    api_request_url = serializers.CharField(source='api_request.url', read_only=True)

    class Meta:
        model = CollectionRequest
        fields = '__all__'


class RequestCollectionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    request_count = serializers.SerializerMethodField()
    requests_detail = CollectionRequestSerializer(source='collection_requests', many=True, read_only=True)
    execution_mode_display = serializers.CharField(source='get_execution_mode_display', read_only=True)

    class Meta:
        model = RequestCollection
        fields = '__all__'

    def get_request_count(self, obj):
        return obj.collection_requests.count()


class RequestCollectionCreateSerializer(serializers.ModelSerializer):
    # 支持嵌套的 collection_requests
    collection_requests = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text='集合请求配置列表，包含: api_request, order_index, stop_on_failure, extract_rules, request_count'
    )
    requests = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text='请求ID列表（向后兼容）'
    )

    class Meta:
        model = RequestCollection
        fields = ['name', 'description', 'project', 'execution_mode', 'collection_requests', 'requests']

    def create(self, validated_data):
        collection_requests_data = validated_data.pop('collection_requests', [])
        requests_ids = validated_data.pop('requests', [])

        # 创建请求集合
        instance = super().create(validated_data)

        # 创建 collection_requests 关联
        if collection_requests_data:
            self._create_collection_requests(instance, collection_requests_data)
        elif requests_ids:
            # 向后兼容旧格式
            self._create_collection_requests_from_ids(instance, requests_ids)

        return instance

    def update(self, instance, validated_data):
        collection_requests_data = validated_data.pop('collection_requests', [])
        requests_ids = validated_data.pop('requests', [])

        # 更新请求集合基本信息
        instance = super().update(instance, validated_data)

        # 删除旧的 collection_requests
        instance.collection_requests.all().delete()

        # 创建新的 collection_requests
        if collection_requests_data:
            self._create_collection_requests(instance, collection_requests_data)
        elif requests_ids:
            # 向后兼容旧格式
            self._create_collection_requests_from_ids(instance, requests_ids)

        return instance

    def _create_collection_requests(self, collection, requests_data):
        """根据详细配置创建 collection_requests"""
        from testmanager_app.models import CollectionRequest

        for i, req_data in enumerate(requests_data):
            CollectionRequest.objects.create(
                collection=collection,
                api_request_id=req_data['api_request'],
                order_index=req_data.get('order_index', i),
                stop_on_failure=req_data.get('stop_on_failure', True),
                extract_rules=req_data.get('extract_rules', []),
                request_count=req_data.get('request_count', 1),
            )

    def _create_collection_requests_from_ids(self, collection, request_ids):
        """仅根据请求ID列表创建 collection_requests（向后兼容）"""
        from testmanager_app.models import CollectionRequest

        for i, request_id in enumerate(request_ids):
            CollectionRequest.objects.create(
                collection=collection,
                api_request_id=request_id,
                order_index=i,
                stop_on_failure=True,
                extract_rules=[],
                request_count=1,
            )


class CollectionExecutionSerializer(serializers.ModelSerializer):
    collection_name = serializers.CharField(source='collection.name', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    pass_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = CollectionExecution
        fields = '__all__'


class CollectionExecutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionExecution
        fields = ['collection']


class ProjectStatisticsSerializer(serializers.Serializer):
    """项目统计信息序列化器"""
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    total_testcases = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    passed_executions = serializers.IntegerField()
    failed_executions = serializers.IntegerField()
    blocked_executions = serializers.IntegerField()
    skipped_executions = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    detail = serializers.JSONField(required=False)


class FeatureTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureTestCase
        fields = '__all__'

class TestResultSerializer(serializers.ModelSerializer):
    api_request_name = serializers.CharField(source='api_request.name', read_only=True)

    class Meta:
        model = TestResult
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    
    user_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Role
        fields = '__all__'
    
    def get_user_count(self, obj):
        return obj.user_links.count()


class UserRoleSerializer(serializers.ModelSerializer):
    """用户角色关联序列化器"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_permission = serializers.CharField(source='role.permission', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'username', 'role_name', 'role_permission', 'created_at']
        read_only_fields = ['created_at']


class UserListSerializer(serializers.ModelSerializer):
    """用户列表序列化器 - 包含角色信息"""

    roles = serializers.SerializerMethodField()
    role_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="角色ID列表"
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        help_text="用户密码（创建用户时必填）"
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'roles', 'role_ids', 'password']
        read_only_fields = ['id', 'date_joined']

    def get_roles(self, obj):
        """获取用户的所有角色
        
        注意：superuser 自动拥有所有权限，不需要分配角色
        但为了前端显示一致性，superuser 也会返回一个虚拟角色信息
        """
        # superuser 自动拥有所有权限，返回虚拟角色信息
        if obj.is_superuser:
            return [{
                'id': 0,
                'name': 'superuser',
                'permission': 'crud',
                'description': '超级管理员角色，拥有所有权限'
            }]
        
        # 普通用户返回实际分配的角色
        roles = UserRole.get_user_roles(obj)
        return RoleSerializer(roles, many=True).data

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        password = validated_data.pop('password', None)

        # 密码是创建用户时的必填项
        if not password:
            raise serializers.ValidationError({'password': '创建用户时密码是必填项'})

        # 创建用户
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # 分配角色（superuser 不需要分配角色，但允许分配，不影响其权限）
        # superuser 自动拥有所有权限，角色分配只是用于记录
        for role_id in role_ids:
            try:
                role = Role.objects.get(id=role_id)
                UserRole.objects.get_or_create(user=user, role=role)
            except Role.DoesNotExist:
                continue

        return user

    def update(self, instance, validated_data):
        role_ids = validated_data.pop('role_ids', None)

        # 更新用户基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()

        # 更新角色
        if role_ids is not None:
            instance.role_links.all().delete()
            for role_id in role_ids:
                try:
                    role = Role.objects.get(id=role_id)
                    UserRole.objects.create(user=instance, role=role)
                except Role.DoesNotExist:
                    continue

        return instance
