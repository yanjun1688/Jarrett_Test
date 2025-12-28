"""
YAML到RequestCollection转换器单元测试
测试YamlToCollectionConverter类的所有方法
"""

import pytest
import base64
from django.test import TestCase
from django.contrib.auth.models import User
from testmanager_app.models import Project, RequestCollection, ApiRequest, CollectionRequest, ApiAssertion
from testmanager_app.services.yaml_converter import YamlToCollectionConverter


class TestYamlToCollectionConverter(TestCase):
    """测试YAML转换器"""

    def setUp(self):
        """设置测试环境"""
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # 创建测试项目
        self.project = Project.objects.create(
            name='测试项目',
            description='这是一个测试项目'
        )

        # 创建转换器实例
        self.converter = YamlToCollectionConverter(
            project_id=self.project.id,
            created_by_id=self.user.id
        )

        # 有效的YAML配置
        self.valid_yaml = """
name: "用户登录流程测试"
description: "完整的用户登录测试流程"
env_vars:
  base_url: "https://api.example.com"
  username: "test_user"
  password: "test_pass123"

steps:
  - name: "获取访问令牌"
    description: "通过用户名密码获取访问令牌"
    request:
      url: "{{base_url}}/api/v1/auth/login"
      method: "POST"
      headers:
        Content-Type: "application/json"
      body:
        username: "{{username}}"
        password: "{{password}}"
    extract:
      - name: "access_token"
        path: "$.data.token"
      - name: "user_id"
        path: "$.data.user.id"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
      - type: "jsonpath"
        path: "$.code"
        expected: "0"
        comparison: "equals"

  - name: "获取用户信息"
    request:
      url: "{{base_url}}/api/v1/user/info"
      method: "GET"
      headers:
        Authorization: "Bearer {{access_token}}"
        Content-Type: "application/json"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
      - type: "jsonpath"
        path: "$['data']['id']"
        expected: "{{user_id}}"
        comparison: "equals"
"""

    # ==================== convert 方法测试 ====================

    def test_convert_valid_yaml(self):
        """测试转换有效的YAML"""
        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="测试集合",
            description="描述信息",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        assert 'collection_id' in result
        assert result['name'] == "测试集合"
        assert result['total_steps'] == 2
        assert result['total_api_requests'] == 2
        assert result['total_assertions'] == 4

        # 验证数据库记录
        collection = RequestCollection.objects.get(id=result['collection_id'])
        assert collection.name == "测试集合"
        assert collection.execution_mode == "chain"
        assert collection.project == self.project

        # 验证ApiRequest创建
        api_requests = ApiRequest.objects.filter(project=self.project)
        assert api_requests.count() == 2

        # 验证CollectionRequest创建
        collection_requests = CollectionRequest.objects.filter(collection=collection)
        assert collection_requests.count() == 2

        # 验证断言创建
        assertions = ApiAssertion.objects.filter(
            api_request__project=self.project
        )
        assert assertions.count() == 4

    def test_convert_validate_only_mode(self):
        """测试仅验证模式，不保存到数据库"""
        initial_count = RequestCollection.objects.count()

        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="验证模式测试",
            description="",
            execution_mode="chain",
            validate_only=True
        )

        assert success is True
        assert 'valid' in result
        assert result['valid'] is True
        assert 'preview' in result

        # 验证没有创建数据库记录
        assert RequestCollection.objects.count() == initial_count

        # 验证预览信息
        preview = result['preview']
        assert preview['total_steps'] == 2
        assert len(preview['steps_preview']) == 2

    def test_convert_invalid_yaml(self):
        """测试转换无效的YAML"""
        invalid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid
      method: "GET"
"""

        success, result = self.converter.convert(
            yaml_content=invalid_yaml,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is False
        assert 'error' in result
        assert 'errors' in result

    # ==================== convert_from_base64 方法测试 ====================

    def test_convert_from_base64(self):
        """测试从Base64编码转换"""
        base64_content = base64.b64encode(self.valid_yaml.encode('utf-8')).decode('utf-8')

        success, result = self.converter.convert_from_base64(
            base64_content=base64_content,
            name="Base64测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        assert 'collection_id' in result

    def test_convert_from_invalid_base64(self):
        """测试从无效的Base64转换"""
        success, result = self.converter.convert_from_base64(
            base64_content="invalid base64!@#",
            name="测试",
            description="",
            execution_mode="chain"
        )

        assert success is False
        assert 'error' in result
        assert 'Base64解码失败' in result['error']

    # ==================== 数据正确性测试 ====================

    def test_convert_creates_correct_collection(self):
        """测试创建的集合数据正确"""
        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="集合测试",
            description="测试描述",
            execution_mode="sequential",
            validate_only=False
        )

        assert success is True

        collection = RequestCollection.objects.get(id=result['collection_id'])
        assert collection.name == "集合测试"
        assert collection.description == "测试描述"
        assert collection.execution_mode == "sequential"
        assert collection.project == self.project
        assert collection.created_by == self.user

    def test_convert_creates_api_requests_with_correct_data(self):
        """测试创建的ApiRequest数据正确"""
        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        # 获取第一个ApiRequest
        api_request = ApiRequest.objects.filter(
            project=self.project,
            name="获取访问令牌"
        ).first()

        assert api_request is not None
        assert "{{base_url}}/api/v1/auth/login" in api_request.url
        assert api_request.method == "POST"
        assert "Content-Type" in str(api_request.headers)

    def test_convert_creates_collection_requests_with_order(self):
        """测试CollectionRequest的顺序正确"""
        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        collection = RequestCollection.objects.get(id=result['collection_id'])
        collection_requests = CollectionRequest.objects.filter(
            collection=collection
        ).order_by('order_index')

        assert collection_requests.count() == 2
        assert collection_requests[0].order_index == 0
        assert collection_requests[1].order_index == 1

    def test_convert_creates_assertions_correctly(self):
        """测试断言创建正确"""
        success, result = self.converter.convert(
            yaml_content=self.valid_yaml,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        # 获取第一个ApiRequest的断言
        api_request = ApiRequest.objects.filter(
            project=self.project,
            name="获取访问令牌"
        ).first()

        assertions = ApiAssertion.objects.filter(api_request=api_request)
        assert assertions.count() == 2

        # 检查状态码断言
        status_assertion = assertions.filter(assertion_type='status_code').first()
        assert status_assertion is not None
        assert status_assertion.comparison == "equals"

        # 检查JSONPath断言
        jsonpath_assertion = assertions.filter(assertion_type='jsonpath').first()
        assert jsonpath_assertion is not None
        assert "$.code" in jsonpath_assertion.field

    # ==================== 边界情况测试 ====================

    def test_convert_yaml_with_no_extract(self):
        """测试没有extract的步骤"""
        yaml_no_extract = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"
"""
        success, result = self.converter.convert(
            yaml_content=yaml_no_extract,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        collection_requests = CollectionRequest.objects.filter(
            collection_id=result['collection_id']
        )
        assert collection_requests.count() == 1

    def test_convert_yaml_with_no_assertions(self):
        """测试没有断言的步骤"""
        yaml_no_assertions = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
"""
        success, result = self.converter.convert(
            yaml_content=yaml_no_assertions,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        api_request = ApiRequest.objects.filter(
            project=self.project
        ).first()

        assertions = ApiAssertion.objects.filter(api_request=api_request)
        assert assertions.count() == 0

    def test_convert_single_step(self):
        """测试单个步骤"""
        yaml_single_step = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
"""
        success, result = self.converter.convert(
            yaml_content=yaml_single_step,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        assert result['total_steps'] == 1

    def test_convert_many_steps(self):
        """测试多个步骤"""
        yaml_many_steps = """
name: "测试"
steps:
"""
        # 生成10个步骤
        for i in range(10):
            yaml_many_steps += f"""
  - name: "步骤{i+1}"
    request:
      url: "http://api{i+1}.com"
      method: "GET"
"""

        success, result = self.converter.convert(
            yaml_content=yaml_many_steps,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        assert result['total_steps'] == 10
        assert result['total_api_requests'] == 10

    def test_convert_with_special_characters_in_values(self):
        """测试值中包含特殊字符"""
        yaml_special_chars = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com?param=value&other=123"
      method: "POST"
      headers:
        Authorization: "Bearer token-with-special.chars_123"
      body:
        data: "test@example.com"
"""
        success, result = self.converter.convert(
            yaml_content=yaml_special_chars,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        assert success is True
        api_request = ApiRequest.objects.filter(
            project=self.project
        ).first()
        assert api_request is not None

    # ==================== 错误处理测试 ====================

    def test_convert_handles_database_error_gracefully(self):
        """测试优雅处理数据库错误"""
        # 创建无效的project_id
        invalid_converter = YamlToCollectionConverter(
            project_id=999999,
            created_by_id=self.user.id
        )

        success, result = invalid_converter.convert(
            yaml_content=self.valid_yaml,
            name="测试",
            description="",
            execution_mode="chain",
            validate_only=False
        )

        # 应该失败，但不会崩溃
        assert success is False
        assert 'error' in result

    def test_validate_only_method(self):
        """测试仅验证方法"""
        is_valid, errors, warnings, preview = self.converter.validate_only(
            self.valid_yaml
        )

        assert is_valid is True
        assert len(errors) == 0
        assert preview is not None
        assert preview['total_steps'] == 2

    def test_validate_only_with_invalid_yaml(self):
        """测试仅验证方法传入无效的YAML"""
        invalid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid
"""

        is_valid, errors, warnings, preview = self.converter.validate_only(
            invalid_yaml
        )

        assert is_valid is False
        assert len(errors) > 0
        assert preview is None

    # ==================== 预览生成测试 ====================

    def test_generate_preview(self):
        """测试预览生成"""
        import yaml as pyyaml
        config = pyyaml.safe_load(self.valid_yaml)

        preview = self.converter._generate_preview(
            config=config,
            name="预览测试",
            description="预览描述",
            execution_mode="chain"
        )

        assert preview['name'] == "预览测试"
        assert preview['description'] == "预览描述"
        assert preview['execution_mode'] == "chain"
        assert preview['total_steps'] == 2
        assert len(preview['steps_preview']) == 2
        assert 'variables' in preview
        assert len(preview['variables']['defined']) > 0

    def test_collect_all_used_variables(self):
        """测试收集所有使用的变量"""
        import yaml as pyyaml
        config = pyyaml.safe_load(self.valid_yaml)

        used_vars = self.converter._collect_all_used_variables(config)

        assert 'base_url' in used_vars
        assert 'username' in used_vars
        assert 'password' in used_vars
        assert 'access_token' in used_vars
