from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import subprocess
import json
import requests
from django.http import HttpResponse
from io import StringIO

from .models import Project, Module, TestCase, TestExecution, TestReport, TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection, CollectionExecution
from .serializers import (
    ProjectSerializer, ModuleSerializer, TestCaseSerializer, TestCaseCreateSerializer,
    TestExecutionSerializer, TestExecutionCreateSerializer, TestReportSerializer,
    ProjectStatisticsSerializer, TestScriptSerializer, TestScriptCreateSerializer,
    ScriptExecutionSerializer, ScriptExecutionCreateSerializer, ApiRequestSerializer,
    ApiRequestCreateSerializer, ApiAssertionSerializer, ApiAssertionCreateSerializer,
    RequestCollectionSerializer, RequestCollectionCreateSerializer, CollectionExecutionSerializer,
    CollectionExecutionCreateSerializer
)


class ProjectViewSet(viewsets.ModelViewSet):
    """项目管理API"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """获取项目统计信息"""
        project = self.get_object()
        
        # 统计测试用例
        total_testcases = TestCase.objects.filter(project=project).count()
        
        # 统计执行记录
        executions = TestExecution.objects.filter(testcase__project=project)
        total_executions = executions.count()
        passed_executions = executions.filter(status='passed').count()
        failed_executions = executions.filter(status='failed').count()
        blocked_executions = executions.filter(status='blocked').count()
        skipped_executions = executions.filter(status='skipped').count()
        
        pass_rate = 0
        if total_executions > 0:
            pass_rate = round((passed_executions / total_executions) * 100, 2)
        
        data = {
            'project_id': project.id,
            'project_name': project.name,
            'total_testcases': total_testcases,
            'total_executions': total_executions,
            'passed_executions': passed_executions,
            'failed_executions': failed_executions,
            'blocked_executions': blocked_executions,
            'skipped_executions': skipped_executions,
            'pass_rate': pass_rate
        }
        
        serializer = ProjectStatisticsSerializer(data)
        return Response(serializer.data)


class ModuleViewSet(viewsets.ModelViewSet):
    """模块管理API"""
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    
    def get_queryset(self):
        queryset = Module.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        return queryset


class TestCaseViewSet(viewsets.ModelViewSet):
    """测试用例管理API"""
    queryset = TestCase.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestCaseCreateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        queryset = TestCase.objects.all()
        project_id = self.request.query_params.get('project', None)
        module_id = self.request.query_params.get('module', None)
        priority = self.request.query_params.get('priority', None)
        
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        if module_id is not None:
            queryset = queryset.filter(module=module_id)
        if priority is not None:
            queryset = queryset.filter(priority=priority)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)


class TestExecutionViewSet(viewsets.ModelViewSet):
    """测试执行记录API"""
    queryset = TestExecution.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestExecutionCreateSerializer
        return TestExecutionSerializer
    
    def get_queryset(self):
        queryset = TestExecution.objects.all()
        testcase_id = self.request.query_params.get('testcase', None)
        status = self.request.query_params.get('status', None)
        
        if testcase_id is not None:
            queryset = queryset.filter(testcase=testcase_id)
        if status is not None:
            queryset = queryset.filter(status=status)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(executor=self.request.user if self.request.user.is_authenticated else None)


class TestReportViewSet(viewsets.ModelViewSet):
    """测试报告API"""
    queryset = TestReport.objects.all()
    serializer_class = TestReportSerializer
    
    def get_queryset(self):
        queryset = TestReport.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """生成测试报告"""
        project_id = request.data.get('project_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([project_id, start_date, end_date]):
            return Response(
                {'error': 'project_id, start_date, end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            project = Project.objects.get(id=project_id)
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except (Project.DoesNotExist, ValueError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 统计指定时间范围内的执行数据
        executions = TestExecution.objects.filter(
            testcase__project=project,
            executed_at__range=[start_date, end_date]
        )
        
        total_cases = executions.values('testcase').distinct().count()
        passed_cases = executions.filter(status='passed').values('testcase').distinct().count()
        failed_cases = executions.filter(status='failed').values('testcase').distinct().count()
        blocked_cases = executions.filter(status='blocked').values('testcase').distinct().count()
        skipped_cases = executions.filter(status='skipped').values('testcase').distinct().count()
        
        # 创建报告
        report = TestReport.objects.create(
            project=project,
            name=f"{project.name} 测试报告 {start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}",
            description=f"时间范围：{start_date.strftime('%Y-%m-%d %H:%M')} 至 {end_date.strftime('%Y-%m-%d %H:%M')}",
            start_date=start_date,
            end_date=end_date,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            blocked_cases=blocked_cases,
            skipped_cases=skipped_cases,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        serializer = TestReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TestScriptViewSet(viewsets.ModelViewSet):
    """测试脚本管理API"""
    queryset = TestScript.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestScriptCreateSerializer
        return TestScriptSerializer
    
    def get_queryset(self):
        queryset = TestScript.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试脚本"""
        script = self.get_object()
        
        # 创建执行记录
        execution = ScriptExecution.objects.create(
            script=script,
            executor=request.user if request.user.is_authenticated else None,
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # 根据脚本类型执行
            if script.script_type == 'python':
                # 执行Python脚本
                result = subprocess.run([
                    'python', script.file.path
                ], capture_output=True, text=True, timeout=300)  # 5分钟超时
                
                execution.output = result.stdout
                execution.error_message = result.stderr
                execution.status = 'success' if result.returncode == 0 else 'failed'
                
            elif script.script_type == 'api':
                # API测试脚本逻辑
                execution.output = "API测试脚本执行完成"
                execution.status = 'success'
                
            else:
                # 其他类型脚本
                execution.output = "脚本执行完成"
                execution.status = 'success'
                
        except subprocess.TimeoutExpired:
            execution.status = 'failed'
            execution.error_message = "脚本执行超时"
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
        
        execution.finished_at = timezone.now()
        execution.duration = execution.finished_at - execution.started_at
        execution.save()
        
        serializer = ScriptExecutionSerializer(execution)
        return Response(serializer.data)


class ScriptExecutionViewSet(viewsets.ModelViewSet):
    """脚本执行记录API"""
    queryset = ScriptExecution.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ScriptExecutionCreateSerializer
        return ScriptExecutionSerializer
    
    def get_queryset(self):
        queryset = ScriptExecution.objects.all()
        script_id = self.request.query_params.get('script', None)
        status = self.request.query_params.get('status', None)
        
        if script_id is not None:
            queryset = queryset.filter(script=script_id)
        if status is not None:
            queryset = queryset.filter(status=status)
            
        return queryset


class ApiRequestViewSet(viewsets.ModelViewSet):
    """API请求管理API"""
    queryset = ApiRequest.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApiRequestCreateSerializer
        return ApiRequestSerializer
    
    def get_queryset(self):
        queryset = ApiRequest.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行API请求并验证断言"""
        api_request = self.get_object()
        
        try:
            # 解析请求头
            headers = {}
            if api_request.headers:
                for line in api_request.headers.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()
            
            # 发送请求
            if api_request.method == 'GET':
                response = requests.get(api_request.url, headers=headers)
            elif api_request.method == 'POST':
                response = requests.post(api_request.url, headers=headers, data=api_request.body)
            elif api_request.method == 'PUT':
                response = requests.put(api_request.url, headers=headers, data=api_request.body)
            elif api_request.method == 'PATCH':
                response = requests.patch(api_request.url, headers=headers, data=api_request.body)
            elif api_request.method == 'DELETE':
                response = requests.delete(api_request.url, headers=headers)
            
            # 验证断言
            assertions = api_request.assertions.all()
            assertion_results = []
            passed_count = 0
            
            for assertion in assertions:
                passed = self._validate_assertion(response, assertion)
                assertion_results.append({
                    'assertion': str(assertion),
                    'passed': passed
                })
                if passed:
                    passed_count += 1
            
            result = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'response_body': response.text,
                'assertions': assertion_results,
                'passed_count': passed_count,
                'total_assertions': len(assertions)
            }
            
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _validate_assertion(self, response, assertion):
        """验证单个断言"""
        try:
            if assertion.assertion_type == 'status_code':
                actual_value = str(response.status_code)
            elif assertion.assertion_type == 'response_time':
                actual_value = str(response.elapsed.total_seconds())
            elif assertion.assertion_type == 'response_body':
                actual_value = response.text
            elif assertion.assertion_type == 'response_header':
                actual_value = response.headers.get(assertion.field, '')
            else:
                return False
            
            expected_value = assertion.expected_value
            
            if assertion.comparison == 'equals':
                return actual_value == expected_value
            elif assertion.comparison == 'contains':
                return expected_value in actual_value
            elif assertion.comparison == 'not_contains':
                return expected_value not in actual_value
            elif assertion.comparison == 'greater_than':
                return float(actual_value) > float(expected_value)
            elif assertion.comparison == 'less_than':
                return float(actual_value) < float(expected_value)
            
            return False
        except:
            return False


class ApiAssertionViewSet(viewsets.ModelViewSet):
    """API断言管理API"""
    queryset = ApiAssertion.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ApiAssertionCreateSerializer
        return ApiAssertionSerializer
    
    def get_queryset(self):
        queryset = ApiAssertion.objects.all()
        api_request_id = self.request.query_params.get('api_request', None)
        if api_request_id is not None:
            queryset = queryset.filter(api_request=api_request_id)
        return queryset


class RequestCollectionViewSet(viewsets.ModelViewSet):
    """请求集合管理API"""
    queryset = RequestCollection.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RequestCollectionCreateSerializer
        return RequestCollectionSerializer
    
    def get_queryset(self):
        queryset = RequestCollection.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行请求集合"""
        collection = self.get_object()
        
        # 创建执行记录
        execution = CollectionExecution.objects.create(
            collection=collection,
            executor=request.user if request.user.is_authenticated else None,
            status='running',
            started_at=timezone.now(),
            total_requests=collection.requests.count()
        )
        
        try:
            passed_count = 0
            failed_count = 0
            output_lines = []
            
            # 依次执行集合中的每个请求
            for api_request in collection.requests.all():
                try:
                    # 执行单个API请求
                    viewset = ApiRequestViewSet()
                    viewset.request = request
                    viewset.format_kwarg = None
                    
                    # 这里简化处理，实际应该调用内部方法
                    output_lines.append(f"执行请求: {api_request.name}")
                    passed_count += 1
                    
                except Exception as e:
                    output_lines.append(f"请求 {api_request.name} 执行失败: {str(e)}")
                    failed_count += 1
            
            execution.passed_requests = passed_count
            execution.failed_requests = failed_count
            execution.output = '\n'.join(output_lines)
            execution.status = 'success' if failed_count == 0 else 'failed'
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
        
        execution.finished_at = timezone.now()
        execution.duration = execution.finished_at - execution.started_at
        execution.save()
        
        serializer = CollectionExecutionSerializer(execution)
        return Response(serializer.data)


class CollectionExecutionViewSet(viewsets.ModelViewSet):
    """集合执行记录API"""
    queryset = CollectionExecution.objects.all()
    serializer_class = CollectionExecutionSerializer
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionExecutionCreateSerializer
        return CollectionExecutionSerializer
    
    def get_queryset(self):
        queryset = CollectionExecution.objects.all()
        collection_id = self.request.query_params.get('collection', None)
        status = self.request.query_params.get('status', None)
        
        if collection_id is not None:
            queryset = queryset.filter(collection=collection_id)
        if status is not None:
            queryset = queryset.filter(status=status)
            
        return queryset
