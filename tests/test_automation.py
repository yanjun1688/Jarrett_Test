import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Project, TestScript, ScriptExecution, ApiRequest, ApiAssertion, RequestCollection

@pytest.mark.django_db
class TestAutomationAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.force_authenticate(user=self.user)
        self.project = Project.objects.create(name='测试项目', description='用于测试的项目')
    
    def test_create_test_script(self):
        """测试创建测试脚本"""
        # 创建一个简单的Python脚本文件
        script_content = b'print("Hello, World!")'
        script_file = SimpleUploadedFile(
            "test_script.py",
            script_content,
            content_type="text/plain"
        )
        
        data = {
            'name': '测试脚本1',
            'description': '这是一个测试脚本',
            'script_type': 'python',
            'project': self.project.id,
            'file': script_file
        }
        
        response = self.client.post('/api/test-scripts/', data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert TestScript.objects.count() == 1
        assert TestScript.objects.get().name == '测试脚本1'
    
    def test_execute_test_script(self):
        """测试执行测试脚本"""
        # 创建一个简单的Python脚本文件
        script_content = b'print("Hello, World!")'
        script_file = SimpleUploadedFile(
            "test_script.py",
            script_content,
            content_type="text/plain"
        )
        
        script = TestScript.objects.create(
            name='测试脚本1',
            description='这是一个测试脚本',
            script_type='python',
            project=self.project,
            file=script_file,
            created_by=self.user
        )
        
        response = self.client.post(f'/api/test-scripts/{script.id}/execute/')
        assert response.status_code == status.HTTP_200_OK
        assert ScriptExecution.objects.count() == 1
        
        execution = ScriptExecution.objects.get()
        assert execution.script == script
        assert execution.status in ['success', 'failed']
    
    def test_create_api_request(self):
        """测试创建API请求"""
        data = {
            'name': '测试API请求',
            'description': '这是一个测试API请求',
            'url': 'https://httpbin.org/get',
            'method': 'GET',
            'headers': 'Content-Type: application/json',
            'body': '',
            'project': self.project.id
        }
        
        response = self.client.post('/api/api-requests/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ApiRequest.objects.count() == 1
        assert ApiRequest.objects.get().name == '测试API请求'
    
    def test_execute_api_request(self):
        """测试执行API请求"""
        api_request = ApiRequest.objects.create(
            name='测试API请求',
            description='这是一个测试API请求',
            url='https://httpbin.org/get',
            method='GET',
            headers='Content-Type: application/json',
            project=self.project,
            created_by=self.user
        )
        
        response = self.client.post(f'/api/api-requests/{api_request.id}/execute/')
        assert response.status_code == status.HTTP_200_OK
        
        # 检查响应中包含预期的字段
        data = response.json()
        assert 'status_code' in data
        assert 'response_time' in data
        assert 'response_body' in data
    
    def test_create_api_assertion(self):
        """测试创建API断言"""
        api_request = ApiRequest.objects.create(
            name='测试API请求',
            url='https://httpbin.org/get',
            method='GET',
            project=self.project,
            created_by=self.user
        )
        
        data = {
            'api_request': api_request.id,
            'assertion_type': 'status_code',
            'field': '',
            'comparison': 'equals',
            'expected_value': '200'
        }
        
        response = self.client.post('/api/api-assertions/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ApiAssertion.objects.count() == 1
        assert ApiAssertion.objects.get().assertion_type == 'status_code'
    
    def test_create_request_collection(self):
        """测试创建请求集合"""
        api_request1 = ApiRequest.objects.create(
            name='测试API请求1',
            url='https://httpbin.org/get',
            method='GET',
            project=self.project,
            created_by=self.user
        )
        
        api_request2 = ApiRequest.objects.create(
            name='测试API请求2',
            url='https://httpbin.org/post',
            method='POST',
            project=self.project,
            created_by=self.user
        )
        
        data = {
            'name': '测试请求集合',
            'description': '这是一个测试请求集合',
            'project': self.project.id,
            'requests': [api_request1.id, api_request2.id]
        }
        
        response = self.client.post('/api/request-collections/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert RequestCollection.objects.count() == 1
        assert RequestCollection.objects.get().name == '测试请求集合'
    
    def test_execute_request_collection(self):
        """测试执行请求集合"""
        api_request1 = ApiRequest.objects.create(
            name='测试API请求1',
            url='https://httpbin.org/get',
            method='GET',
            project=self.project,
            created_by=self.user
        )
        
        collection = RequestCollection.objects.create(
            name='测试请求集合',
            description='这是一个测试请求集合',
            project=self.project,
            created_by=self.user
        )
        collection.requests.add(api_request1)
        
        response = self.client.post(f'/api/request-collections/{collection.id}/execute/')
        assert response.status_code == status.HTTP_200_OK
        
        # 检查是否创建了执行记录
        assert CollectionExecution.objects.count() == 1
        
        execution = CollectionExecution.objects.get()
        assert execution.collection == collection
        assert execution.status in ['success', 'failed']