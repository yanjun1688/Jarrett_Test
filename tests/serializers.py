from rest_framework import serializers
from .models import Project, Module, TestCase, TestExecution, TestReport, TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection, CollectionExecution
from django.contrib.auth.models import User


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
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    
    class Meta:
        model = TestExecution
        fields = '__all__'


class TestExecutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestExecution
        fields = ['testcase', 'status', 'actual_result', 'comments', 'execution_duration']


class TestReportSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    pass_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = TestReport
        fields = '__all__'


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
        fields = ['name', 'description', 'script_type', 'project', 'file']


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
    class Meta:
        model = ApiAssertion
        fields = ['api_request', 'assertion_type', 'field', 'comparison', 'expected_value']


class RequestCollectionSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    request_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RequestCollection
        fields = '__all__'
    
    def get_request_count(self, obj):
        return obj.requests.count()


class RequestCollectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestCollection
        fields = ['name', 'description', 'project', 'requests']


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