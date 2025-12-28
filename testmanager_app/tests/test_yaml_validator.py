"""
YAML验证器单元测试
测试YamlValidator类的所有方法
"""

import pytest
import yaml
from django.test import TestCase
from testmanager_app.services.yaml_validator import YamlValidator


class TestYamlValidator(TestCase):
    """测试YAML验证器"""

    def setUp(self):
        """设置测试环境"""
        self.validator = YamlValidator()

    # ==================== 基础结构验证测试 ====================

    def test_validate_valid_yaml(self):
        """测试有效的YAML格式"""
        valid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(valid_yaml)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_yaml_syntax(self):
        """测试无效的YAML语法"""
        invalid_yaml = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    key: value: invalid  # 无效的YAML语法
"""
        is_valid, errors, warnings = self.validator.validate(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0
        assert any(e['type'] == 'yaml_syntax' for e in errors)

    def test_validate_missing_required_fields(self):
        """测试缺少必填字段"""
        yaml_without_name = """
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_without_name)
        assert is_valid is False
        assert any(e['type'] == 'missing_field' and 'name' in e['message'] for e in errors)

    def test_validate_missing_steps(self):
        """测试缺少steps字段"""
        yaml_without_steps = """
name: "测试"
description: "没有步骤"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_without_steps)
        assert is_valid is False
        assert any(e['type'] == 'missing_field' and 'steps' in e['message'] for e in errors)

    def test_validate_empty_steps(self):
        """测试空的steps列表"""
        yaml_empty_steps = """
name: "测试"
steps: []
"""
        is_valid, errors, warnings = self.validator.validate(yaml_empty_steps)
        assert is_valid is False
        assert any(e['type'] == 'empty_list' for e in errors)

    def test_validate_steps_not_list(self):
        """测试steps不是列表"""
        yaml_steps_not_list = """
name: "测试"
steps:
  name: "步骤1"
  request:
    url: "http://api.com"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_steps_not_list)
        assert is_valid is False
        assert any(e['type'] == 'invalid_type' for e in errors)

    # ==================== 步骤结构验证测试 ====================

    def test_validate_step_missing_request(self):
        """测试步骤缺少request字段"""
        yaml_step_no_request = """
name: "测试"
steps:
  - name: "步骤1"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_step_no_request)
        assert is_valid is False
        assert any('request' in e['message'] for e in errors)

    def test_validate_step_missing_url(self):
        """测试步骤缺少url"""
        yaml_step_no_url = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_step_no_url)
        assert is_valid is False
        assert any('url' in e['message'] for e in errors)

    def test_validate_step_missing_method(self):
        """测试步骤缺少method"""
        yaml_step_no_method = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_step_no_method)
        assert is_valid is False
        assert any('method' in e['message'] for e in errors)

    def test_validate_invalid_http_method(self):
        """测试无效的HTTP方法"""
        yaml_invalid_method = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "INVALID_METHOD"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_invalid_method)
        assert is_valid is False
        assert any("无效的HTTP方法" in e['message'] for e in errors)

    # ==================== 变量语法验证测试 ====================

    def test_validate_valid_variable_syntax(self):
        """测试有效的变量语法"""
        yaml_valid_vars = """
name: "测试"
env_vars:
  base_url: "http://api.com"
steps:
  - name: "步骤1"
    request:
      url: "{{base_url}}/users"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_valid_vars)
        assert is_valid is True

    def test_validate_unmatched_braces(self):
        """测试不匹配的括号"""
        yaml_unmatched = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{base_url/users"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_unmatched)
        assert is_valid is False
        assert any('缺少对应的' in e['message'] for e in errors)

    def test_validate_invalid_variable_name(self):
        """测试无效的变量名"""
        yaml_invalid_var = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid var}}/users"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_invalid_var)
        assert is_valid is False
        assert any('无效的变量名' in e['message'] for e in errors)

    def test_validate_variable_with_default(self):
        """测试带默认值的变量"""
        yaml_with_default = """
name: "测试"
env_vars:
  timeout: "30"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
      timeout: "{{timeout|default:'30'}}"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_with_default)
        assert is_valid is True

    def test_validate_undefined_variable_warning(self):
        """测试未定义变量的警告"""
        yaml_undefined_var = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{undefined_var}}/users"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_undefined_var)
        # 未定义变量应该是warning，不是error
        assert is_valid is True
        assert len(warnings) > 0
        assert any('未定义' in w['message'] for w in warnings)

    # ==================== JSONPath验证测试 ====================

    def test_validate_valid_jsonpath(self):
        """测试有效的JSONPath"""
        yaml_valid_jsonpath = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    extract:
      - name: "token"
        path: "$['data']['token']"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_valid_jsonpath, check_jsonpath=True)
        assert is_valid is True

    def test_validate_invalid_jsonpath(self):
        """测试无效的JSONPath"""
        yaml_invalid_jsonpath = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    extract:
      - name: "token"
        path: "$.data[0].token"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_invalid_jsonpath, check_jsonpath=True)
        assert is_valid is False
        assert any('无效的JSONPath' in e['message'] for e in errors)

    def test_validate_jsonpath_in_assertion(self):
        """测试断言中的JSONPath"""
        yaml_jsonpath_assertion = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - type: "jsonpath"
        path: "$.code"
        expected: "0"
        comparison: "equals"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_jsonpath_assertion, check_jsonpath=True)
        assert is_valid is True

    # ==================== 断言验证测试 ====================

    def test_validate_valid_assertions(self):
        """测试有效的断言"""
        yaml_valid_assertions = """
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
      - type: "jsonpath"
        path: "$.code"
        expected: "0"
        comparison: "equals"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_valid_assertions)
        assert is_valid is True

    def test_validate_missing_assertion_type(self):
        """测试缺少断言类型"""
        yaml_no_assertion_type = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - expected: 200
        comparison: "equals"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_no_assertion_type)
        assert is_valid is False
        assert any('断言缺少必填字段: type' in e['message'] for e in errors)

    def test_validate_invalid_assertion_type(self):
        """测试无效的断言类型"""
        yaml_invalid_assertion_type = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - type: "invalid_type"
        expected: 200
        comparison: "equals"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_invalid_assertion_type)
        assert is_valid is False
        assert any('断言类型不合法' in e['message'] for e in errors)

    def test_validate_jsonpath_assertion_missing_path(self):
        """测试JSONPath断言缺少path"""
        yaml_jsonpath_no_path = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - type: "jsonpath"
        expected: "0"
        comparison: "equals"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_jsonpath_no_path)
        assert is_valid is False
        assert any('JSONPath断言缺少必填字段: path' in e['message'] for e in errors)

    def test_validate_invalid_comparison_type(self):
        """测试无效的比较类型"""
        yaml_invalid_comparison = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com"
      method: "GET"
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "invalid_comparison"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_invalid_comparison)
        assert is_valid is False
        assert any('比较方式不合法' in e['message'] for e in errors)

    # ==================== 复杂场景测试 ====================

    def test_validate_complete_yaml(self):
        """测试完整的YAML配置"""
        complete_yaml = """
name: "用户登录流程测试"
description: "完整的用户登录和业务测试流程"
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
    assertions:
      - type: "status_code"
        expected: 200
        comparison: "equals"

execution:
  mode: "chain"
  continue_on_failure: false
"""
        is_valid, errors, warnings = self.validator.validate(complete_yaml, check_jsonpath=True)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_with_all_comparison_types(self):
        """测试所有比较类型"""
        yaml_all_comparisons = """
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
      - type: "status_code"
        expected: 201
        comparison: "not_equals"
      - type: "jsonpath"
        path: "$.message"
        expected: "success"
        comparison: "contains"
      - type: "jsonpath"
        path: "$.count"
        expected: 10
        comparison: "gt"
      - type: "jsonpath"
        path: "$.count"
        expected: 10
        comparison: "gte"
      - type: "jsonpath"
        path: "$.count"
        expected: 10
        comparison: "lt"
      - type: "jsonpath"
        path: "$.count"
        expected: 10
        comparison: "lte"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_all_comparisons)
        assert is_valid is True

    def test_validate_nested_variables(self):
        """测试嵌套变量"""
        yaml_nested_vars = """
name: "测试"
env_vars:
  user:
    name: "test"
steps:
  - name: "步骤1"
    request:
      url: "http://api.com/{{user.name}}"
      method: "GET"
"""
        is_valid, errors, warnings = self.validator.validate(yaml_nested_vars)
        assert is_valid is True

    def test_validate_without_check_options(self):
        """测试不检查变量和JSONPath"""
        yaml_invalid = """
name: "测试"
steps:
  - name: "步骤1"
    request:
      url: "{{invalid_var}}/users"
      method: "GET"
    extract:
      - name: "token"
        path: "invalid jsonpath {{{"
"""
        # 不检查变量和JSONPath
        is_valid, errors, warnings = self.validator.validate(
            yaml_invalid,
            check_variables=False,
            check_jsonpath=False
        )
        # 应该通过，因为我们跳过了这些检查
        assert is_valid is True
