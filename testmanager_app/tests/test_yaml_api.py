"""
YAML配置工具API集成测试
测试yaml_to_collection和validate_yaml_config API端点
"""

import pytest
import json
import base64
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from testmanager_app.models import Project, RequestCollection, ApiRequest


class TestYamlAPI(TestCase):
    """测试YAML配置工具API"""

    def setUp(self):
        """设置测试环境"""
        self.client = Client()

        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # 创建Token
        self.token = Token.objects.create(user=self.user)

        # 创建测试项目
        self.project = Project.objects.create(
            name='测试项目',
            description='这是一个测试项目'
        )

        # 有效的YAML配置
        self.valid_yaml = """
name: "API集成测试"
description: "测试API集成"
env_vars:
  base_url: "https://api.example.com"

steps:
  - name: "获取Token"
    request:
      url: "{{base_url}}/api/login"
      method: "POST"
      headers:
        Content-Type: "application/json"
      body:
        username: "test"
    extract:
      - name: "token"
        path: "$.data.token"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"

  - name: "查询数据"
    request:
      url: "{{base_url}}/api/data"
      method: "GET"
      headers:
        Authorization: "Bearer {{token}}"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
"""

        # Base64编码的YAML
        self.base64_yaml = base64.b64encode(
            self.valid_yaml.encode('utf-8')
        ).decode('utf-8')

    def _get_auth_header(self):
        """获取认证头"""
        return {
            'HTTP_AUTHORIZATION': f'Token {self.token.key}',
            'CONTENT_TYPE': 'application/json'
        }

    # ==================== yaml_to_collection API测试 ====================

    def test_yaml_to_collection_success(self):
        """测试成功转换YAML到Collection"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        data = {
            'name': '测试API集合',
            'description': 'API测试描述',
            'yaml_content': self.base64_yaml,
            'execution_mode': 'chain',
            'validate_only': False
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 201
        response_data = json.loads(response.content)

        assert response_data['code'] == 201
        assert '转换成功' in response_data['message']
        assert 'collection_id' in response_data['data']
        assert response_data['data']['name'] == '测试API集合'
        assert response_data['data']['total_steps'] == 2

        # 验证数据库记录
        collection_id = response_data['data']['collection_id']
        collection = RequestCollection.objects.get(id=collection_id)
        assert collection.name == '测试API集合'
        assert collection.execution_mode == 'chain'

    def test_yaml_to_collection_validate_only(self):
        """测试仅验证模式"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        data = {
            'name': '验证测试',
            'description': '',
            'yaml_content': self.base64_yaml,
            'execution_mode': 'chain',
            'validate_only': True
        }

        initial_count = RequestCollection.objects.count()

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)

        assert response_data['code'] == 200
        assert '验证成功' in response_data['message']
        assert 'preview' in response_data['data']
        assert response_data['data']['valid'] is True

        # 验证没有创建数据库记录
        assert RequestCollection.objects.count() == initial_count

    def test_yaml_to_collection_missing_name(self):
        """测试缺少name参数"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        data = {
            'description': '没有名称',
            'yaml_content': self.base64_yaml,
            'execution_mode': 'chain'
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['code'] == 400

    def test_yaml_to_collection_missing_yaml_content(self):
        """测试缺少yaml_content参数"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        data = {
            'name': '测试',
            'description': '',
            'execution_mode': 'chain'
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['code'] == 400

    def test_yaml_to_collection_invalid_yaml(self):
        """测试无效的YAML格式"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        invalid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid
      method: "GET"
"""
        base64_invalid = base64.b64encode(invalid_yaml.encode('utf-8')).decode('utf-8')

        data = {
            'name': '测试',
            'yaml_content': base64_invalid,
            'execution_mode': 'chain'
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 422
        response_data = json.loads(response.content)
        assert response_data['code'] == 422
        assert 'errors' in response_data

    def test_yaml_to_collection_unauthorized(self):
        """测试未授权访问"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        data = {
            'name': '测试',
            'yaml_content': self.base64_yaml,
            'execution_mode': 'chain'
        }

        # 不发送认证头
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 401

    def test_yaml_to_collection_wrong_method(self):
        """测试错误的HTTP方法"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        # 使用GET而不是POST
        response = self.client.get(url, **self._get_auth_header())

        assert response.status_code == 405

    def test_yaml_to_collection_different_execution_modes(self):
        """测试不同的执行模式"""
        url = reverse('yaml-to-collection', args=[self.project.id])

        for mode in ['chain', 'sequential', 'concurrent']:
            data = {
                'name': f'模式测试_{mode}',
                'yaml_content': self.base64_yaml,
                'execution_mode': mode
            }

            response = self.client.post(
                url,
                data=json.dumps(data),
                **self._get_auth_header()
            )

            assert response.status_code == 201
            response_data = json.loads(response.content)

            collection_id = response_data['data']['collection_id']
            collection = RequestCollection.objects.get(id=collection_id)
            assert collection.execution_mode == mode

    # ==================== validate_yaml_config API测试 ====================

    def test_validate_yaml_config_success(self):
        """测试成功验证YAML"""
        url = reverse('validate-yaml', args=[self.project.id])

        data = {
            'yaml_content': self.base64_yaml,
            'check_variables': True,
            'check_jsonpath': True
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)

        assert response_data['code'] == 200
        assert response_data['data']['valid'] is True
        assert 'stats' in response_data['data']
        assert response_data['data']['stats']['total_steps'] == 2

    def test_validate_yaml_config_invalid(self):
        """测试验证无效的YAML"""
        url = reverse('validate-yaml', args=[self.project.id])

        invalid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid
      method: "GET"
"""
        base64_invalid = base64.b64encode(invalid_yaml.encode('utf-8')).decode('utf-8')

        data = {
            'yaml_content': base64_invalid,
            'check_variables': True,
            'check_jsonpath': True
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 422
        response_data = json.loads(response.content)

        assert response_data['code'] == 422
        assert response_data['data']['valid'] is False
        assert 'errors' in response_data['data']
        assert len(response_data['data']['errors']) > 0

    def test_validate_yaml_config_missing_content(self):
        """测试缺少yaml_content参数"""
        url = reverse('validate-yaml', args=[self.project.id])

        data = {
            'check_variables': True,
            'check_jsonpath': True
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 400
        response_data = json.loads(response.content)
        assert response_data['code'] == 400

    def test_validate_yaml_config_skip_checks(self):
        """测试跳过某些验证检查"""
        url = reverse('validate-yaml', args=[self.project.id])

        # 包含未定义变量和无效JSONPath的YAML
        yaml_with_issues = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{undefined_var}}/api"
      method: "GET"
    extract:
      - name: "token"
        path: "$.invalid[path["
"""
        base64_yaml = base64.b64encode(yaml_with_issues.encode('utf-8')).decode('utf-8')

        # 跳过变量和JSONPath检查
        data = {
            'yaml_content': base64_yaml,
            'check_variables': False,
            'check_jsonpath': False
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert response_data['data']['valid'] is True

    def test_validate_yaml_config_unauthorized(self):
        """测试未授权访问"""
        url = reverse('validate-yaml', args=[self.project.id])

        data = {
            'yaml_content': self.base64_yaml
        }

        # 不发送认证头
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 401

    # ==================== 集成工作流测试 ====================

    def test_full_workflow_validate_then_create(self):
        """测试完整工作流：先验证，再创建"""
        # 第一步：验证
        validate_url = reverse('validate-yaml', args=[self.project.id])
        validate_data = {
            'yaml_content': self.base64_yaml
        }

        validate_response = self.client.post(
            validate_url,
            data=json.dumps(validate_data),
            **self._get_auth_header()
        )

        assert validate_response.status_code == 200
        validate_result = json.loads(validate_response.content)
        assert validate_result['data']['valid'] is True

        # 第二步：创建
        create_url = reverse('yaml-to-collection', args=[self.project.id])
        create_data = {
            'name': '完整工作流测试',
            'description': '验证后创建',
            'yaml_content': self.base64_yaml,
            'execution_mode': 'chain',
            'validate_only': False
        }

        create_response = self.client.post(
            create_url,
            data=json.dumps(create_data),
            **self._get_auth_header()
        )

        assert create_response.status_code == 201
        create_result = json.loads(create_response.content)
        assert 'collection_id' in create_result['data']

        # 第三步：查询验证
        collection_id = create_result['data']['collection_id']
        collection = RequestCollection.objects.get(id=collection_id)
        assert collection.name == '完整工作流测试'
        assert collection.project == self.project

    # ==================== 边界条件测试 ====================

    def test_large_yaml_file(self):
        """测试大YAML文件"""
        # 生成包含50个步骤的YAML
        large_yaml = """
name: "大文件测试"
env_vars:
  base_url: "https://api.example.com"

steps:
"""
        for i in range(50):
            large_yaml += f"""
  - name: "步骤{i+1}"
    request:
      url: "{{base_url}}/api/endpoint{i}"
      method: "GET"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
"""

        base64_large = base64.b64encode(large_yaml.encode('utf-8')).decode('utf-8')

        url = reverse('yaml-to-collection', args=[self.project.id])
        data = {
            'name': '大文件测试',
            'yaml_content': base64_large,
            'execution_mode': 'sequential'
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 201
        response_data = json.loads(response.content)
        assert response_data['data']['total_steps'] == 50

    def test_yaml_with_unicode_characters(self):
        """测试包含Unicode字符的YAML"""
        yaml_with_unicode = """
name: "中文测试名称"
description: "描述信息包含中文和Unicode: 你好世界 🌍"
steps:
  - name: "步骤1 - 中文"
    request:
      url: "http://api.example.com"
      method: "GET"
"""

        base64_unicode = base64.b64encode(yaml_with_unicode.encode('utf-8')).decode('utf-8')

        url = reverse('yaml-to-collection', args=[self.project.id])
        data = {
            'name': 'Unicode测试',
            'yaml_content': base64_unicode,
            'execution_mode': 'chain'
        }

        response = self.client.post(
            url,
            data=json.dumps(data),
            **self._get_auth_header()
        )

        assert response.status_code == 201
        response_data = json.loads(response.content)
        collection_id = response_data['data']['collection_id']
        collection = RequestCollection.objects.get(id=collection_id)
        assert collection.name == 'Unicode测试'
