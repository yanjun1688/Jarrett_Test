"""
UI测试应用的序列化器
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UITestScript,
    UITestExecution,
)


class UITestScriptSerializer(serializers.ModelSerializer):
    """UI测试脚本序列化器"""
    actions = serializers.JSONField(default=list, help_text="动作列表（统一格式）")
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = UITestScript
        fields = ['id', 'name', 'description', 'project', 'project_name',
                  'created_by', 'created_by_username', 'created_at', 'updated_at',
                  'is_active', 'actions', 'browser_type', 'headless', 
                  'viewport_width', 'viewport_height', 'timeout']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class UITestScriptCreateSerializer(serializers.ModelSerializer):
    """UI测试脚本创建序列化器（使用actions格式）"""
    actions = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="动作列表"
    )
    # 保留steps字段用于向后兼容（将自动转换为actions）
    steps = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="已废弃，请使用actions字段（如果提供steps，将自动转换为actions）"
    )
    
    class Meta:
        model = UITestScript
        fields = ['name', 'description', 'project', 'is_active',
                  'actions', 'browser_type', 'headless', 'viewport_width',
                  'viewport_height', 'timeout', 'steps']
    
    def create(self, validated_data):
        actions = validated_data.pop('actions', [])
        steps_data = validated_data.pop('steps', [])  # 向后兼容
        
        # 如果提供了steps但没有actions，转换steps为actions
        if not actions and steps_data:
            from .converters.action_converter import convert_to_actions
            actions = convert_to_actions(steps_data, 'steps')
        
        validated_data['created_by'] = self.context['request'].user
        validated_data['actions'] = actions
        
        script = UITestScript.objects.create(**validated_data)
        return script


class UITestExecutionSerializer(serializers.ModelSerializer):
    """UI测试执行记录序列化器"""
    script_name = serializers.CharField(source='script.name', read_only=True)
    executed_by_username = serializers.CharField(source='executed_by.username', read_only=True)
    
    class Meta:
        model = UITestExecution
        fields = ['id', 'script', 'script_name', 'executed_by', 'executed_by_username',
                  'status', 'started_at', 'completed_at', 'duration',
                  'result_summary', 'error_message', 'screenshots', 'execution_log',
                  'created_at']
        read_only_fields = ['id', 'status', 'started_at', 'completed_at', 'duration',
                           'result_summary', 'error_message', 'screenshots', 'execution_log',
                           'created_at']


class UITestExecutionListSerializer(serializers.ModelSerializer):
    """轻量级UI测试执行记录序列化器，用于列表展示，优化性能"""
    script_name = serializers.CharField(source='script.name', read_only=True)
    executed_by_username = serializers.CharField(source='executed_by.username', read_only=True)
    
    class Meta:
        model = UITestExecution
        fields = [
            'id', 'script', 'script_name', 'status', 
            'executed_by', 'executed_by_username', 'created_at'
        ]


class ScriptExecutionRequestSerializer(serializers.Serializer):
    """脚本执行请求序列化器"""
    script_id = serializers.IntegerField()
    # 可选：覆盖浏览器配置
    browser_type = serializers.CharField(required=False)
    headless = serializers.BooleanField(required=False)
    viewport_width = serializers.IntegerField(required=False)
    viewport_height = serializers.IntegerField(required=False)
    timeout = serializers.IntegerField(required=False)


class RecordedStepSerializer(serializers.Serializer):
    """录制的步骤序列化器"""
    action_type = serializers.CharField()
    element_locator = serializers.DictField(required=False, allow_null=True)
    action_params = serializers.DictField(required=False, default=dict)
    description = serializers.CharField(required=False, allow_blank=True, default='')


class ScriptRecordingSerializer(serializers.Serializer):
    """脚本录制序列化器"""
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default='')
    project_id = serializers.IntegerField(required=False, allow_null=True)
    steps = serializers.ListField(child=RecordedStepSerializer())



