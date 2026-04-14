from __future__ import annotations
from typing import Any, Dict, List, Optional
from rest_framework import serializers
from core.models import Project, Module, TestCase, TestExecution
from testmanager_app.models import TestReport, TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection, CollectionExecution, FeatureTestCase, CollectionRequest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


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
    """测试用例创建序列化器（用于创建和更新操作）"""
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
        fields = ['test_type', 'testcase', 'api_request', 'status', 'actual_result', 'comments', 'duration', 'api_response_data', 'api_logs']


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

    def validate_project_id(self, value: int) -> Project:
        """验证 project_id 并返回 Project 对象"""
        try:
            return Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError(f'Project with id {value} not found')

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证业务规则：日期范围合理性"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                'date_range': 'Start date cannot be later than end date'
            })

        if end_date and end_date > timezone.now():
            raise serializers.ValidationError({
                'end_date': 'End date cannot be in the future'
            })

        if start_date and end_date:
            max_range = timedelta(days=365)
            if end_date - start_date > max_range:
                raise serializers.ValidationError({
                    'date_range': 'Date range cannot exceed 1 year'
                })

        return data

    def to_representation(self, instance: tuple) -> Dict[str, Optional[str]]:
        """序列化输出（用于调试）"""
        return {
            'project_id': str(instance[0].id) if instance else None,
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
        fields = ['id', 'name', 'description', 'script_type', 'content', 'project', 'created_by']
        read_only_fields = ['id', 'created_by']


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
    
    field_path = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )
    
    class Meta:
        model = ApiAssertion
        fields = ['api_request', 'assertion_type', 'field_path', 'comparison', 'expected_value']
    
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """验证字段路径的条件必填"""
        assertion_type = attrs.get('assertion_type')
        field_path = attrs.get('field_path')
        if field_path is None:
            field_path = ''
        elif isinstance(field_path, str):
            field_path = field_path.strip()
        else:
            field_path = str(field_path).strip()
        
        attrs['field_path'] = field_path
        
        if assertion_type in ['response_body_field', 'response_header_field']:
            if not field_path:
                raise serializers.ValidationError({
                    'field_path': f'当断言类型为"{dict(ApiAssertion.ASSERTION_TYPE_CHOICES).get(assertion_type, assertion_type)}"时，字段路径为必填项'
                })
        
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

    def get_request_count(self, obj: RequestCollection) -> int:
        return obj.collection_requests.count()  # type: ignore[attr-defined]


class RequestCollectionCreateSerializer(serializers.ModelSerializer):
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
        fields = ['id', 'name', 'description', 'project', 'execution_mode', 'variables', 'collection_requests', 'requests']
        read_only_fields = ['id']

    def create(self, validated_data: Dict[str, Any]) -> RequestCollection:
        collection_requests_data = validated_data.pop('collection_requests', [])
        requests_ids = validated_data.pop('requests', [])

        instance = super().create(validated_data)

        if collection_requests_data:
            self._create_collection_requests(instance, collection_requests_data)
        elif requests_ids:
            self._create_collection_requests_from_ids(instance, requests_ids)

        return instance

    def update(self, instance: RequestCollection, validated_data: Dict[str, Any]) -> RequestCollection:
        collection_requests_data = validated_data.pop('collection_requests', [])
        requests_ids = validated_data.pop('requests', [])

        instance = super().update(instance, validated_data)

        instance.collection_requests.all().delete()  # type: ignore[attr-defined]

        if collection_requests_data:
            self._create_collection_requests(instance, collection_requests_data)
        elif requests_ids:
            self._create_collection_requests_from_ids(instance, requests_ids)

        return instance

    def _create_collection_requests(self, collection: RequestCollection, requests_data: List[Dict[str, Any]]) -> None:
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

    def _create_collection_requests_from_ids(self, collection: RequestCollection, request_ids: List[int]) -> None:
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
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = FeatureTestCase
        fields = '__all__'


class UserListSerializer(serializers.ModelSerializer):
    """用户列表序列化器"""

    password = serializers.CharField(
        write_only=True,
        required=False,
        help_text="用户密码（创建用户时必填）"
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'password',
            'date_joined'
        ]
        read_only_fields = ['date_joined', 'is_superuser', 'is_staff']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if self.instance is None:
            if not attrs.get('password'):
                raise serializers.ValidationError({'password': '创建用户时密码是必填项'})
        return attrs

    def create(self, validated_data: Dict[str, Any]) -> User:
        password = validated_data.pop('password', None)

        if not password:
            raise serializers.ValidationError({'password': '创建用户时密码是必填项'})

        user = User.objects.create_user(**validated_data, password=password)
        return user

    def update(self, instance: User, validated_data: Dict[str, Any]) -> User:
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """知识库序列化器"""
    
    class Meta:
        from core.models.knowledge import KnowledgeBase
        model = KnowledgeBase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """知识文档序列化器"""
    
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True)
    
    class Meta:
        from core.models.knowledge import KnowledgeDocument
        model = KnowledgeDocument
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AgentConversationSerializer(serializers.ModelSerializer):
    """Agent对话历史序列化器"""
    
    class Meta:
        from core.models.agents import AgentConversation
        model = AgentConversation
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class AgentExecutionSerializer(serializers.ModelSerializer):
    """Agent执行记录序列化器"""
    
    class Meta:
        from core.models.agents import AgentExecution
        model = AgentExecution
        fields = '__all__'
        read_only_fields = ['id', 'started_at', 'ended_at']