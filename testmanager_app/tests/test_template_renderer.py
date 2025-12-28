"""
Unit tests for template_renderer.py

Tests template rendering functionality with various scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from testmanager_app.utils.template_renderer import TemplateRenderer


class TestTemplateRenderer:
    """Test the TemplateRenderer class."""

    def test_render_string_with_simple_variable(self):
        """Test rendering string with simple variable substitution."""
        template = "Hello {{name}}!"
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == "Hello John!"

    def test_render_string_with_multiple_variables(self):
        """Test rendering string with multiple variables."""
        template = "User {{user.name}} has email {{user.email}}"
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }

        result = TemplateRenderer.render(template, context)

        assert result == "User John Doe has email john@example.com"

    def test_render_string_with_default_value(self):
        """Test rendering string with default value."""
        template = "Welcome {{user.name|default:\"Guest\"}}!"
        context = {}  # Empty context

        result = TemplateRenderer.render(template, context)

        assert result == "Welcome Guest!"

    def test_render_string_with_default_value_not_used(self):
        """Test rendering string when default value is not needed."""
        template = "Welcome {{user.name|default:\"Guest\"}}!"
        context = {"user": {"name": "John"}}

        result = TemplateRenderer.render(template, context)

        assert result == "Welcome John!"

    def test_render_string_with_list_access(self):
        """Test rendering string with list access."""
        template = "First item: {{items.0.name}}, Second item: {{items.1.name}}"
        context = {
            "items": [
                {"name": "Item 1"},
                {"name": "Item 2"}
            ]
        }

        result = TemplateRenderer.render(template, context)

        assert result == "First item: Item 1, Second item: Item 2"

    def test_render_string_with_global_default(self):
        """Test rendering string with global default value."""
        template = "Value: {{missing_value}}"
        context = {}

        result = TemplateRenderer.render(template, context, default_value="N/A")

        assert result == "Value: N/A"

    def test_render_string_with_both_defaults(self):
        """Test rendering string with both local and global defaults."""
        template = "Local: {{value1|default:\"LocalDefault\"}}, Global: {{value2}}"
        context = {}

        result = TemplateRenderer.render(template, context, default_value="GlobalDefault")

        assert result == "Local: LocalDefault, Global: GlobalDefault"

    def test_render_dict_template(self):
        """Test rendering dictionary template."""
        template = {
            "name": "{{user.name}}",
            "email": "{{user.email|default:\"noemail@example.com\"}}",
            "age": "{{user.age|default:\"25\"}}"
        }
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
                # age is missing, should use default
            }
        }

        result = TemplateRenderer.render(template, context)

        expected = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": "25"
        }
        assert result == expected

    def test_render_list_template(self):
        """Test rendering list template."""
        template = [
            "Name: {{user.name}}",
            "Email: {{user.email}}",
            "Role: {{user.role|default:\"user\"}}"
        ]
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }

        result = TemplateRenderer.render(template, context)

        expected = [
            "Name: John Doe",
            "Email: john@example.com",
            "Role: user"
        ]
        assert result == expected

    def test_render_nested_structure(self):
        """Test rendering nested dictionary and list structures."""
        template = {
            "user": {
                "profile": {
                    "name": "{{user.name}}",
                    "contacts": [
                        "{{user.email}}",
                        "{{user.phone|default:\"No phone\"}}"
                    ]
                }
            },
            "settings": [
                {"key": "theme", "value": "{{settings.theme|default:\"light\"}}"},
                {"key": "language", "value": "{{settings.lang|default:\"en\"}}"}
            ]
        }
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "settings": {
                "theme": "dark"
            }
        }

        result = TemplateRenderer.render(template, context)

        expected = {
            "user": {
                "profile": {
                    "name": "John Doe",
                    "contacts": [
                        "john@example.com",
                        "No phone"
                    ]
                }
            },
            "settings": [
                {"key": "theme", "value": "dark"},
                {"key": "language", "value": "en"}
            ]
        }
        assert result == expected

    def test_render_non_string_values(self):
        """Test rendering with non-string template values."""
        template = {
            "string_value": "{{value}}",
            "number_value": 42,
            "boolean_value": True,
            "none_value": None,
            "list_value": ["{{item}}", 123, True]
        }
        context = {"value": "test", "item": "list_item"}

        result = TemplateRenderer.render(template, context)

        expected = {
            "string_value": "test",
            "number_value": 42,
            "boolean_value": True,
            "none_value": None,
            "list_value": ["list_item", 123, True]
        }
        assert result == expected

    def test_render_empty_template(self):
        """Test rendering empty template."""
        template = ""
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == ""

    def test_render_empty_context(self):
        """Test rendering with empty context."""
        template = "Hello {{name|default:\"World\"}}!"
        context = {}

        result = TemplateRenderer.render(template, context)

        assert result == "Hello World!"

    def test_render_no_variables(self):
        """Test rendering template with no variables."""
        template = "This is a plain text without variables."
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == "This is a plain text without variables."

    def test_render_missing_nested_variable(self):
        """Test rendering with missing nested variable."""
        template = "User: {{user.profile.name}}"
        context = {"user": {}}  # Missing profile

        result = TemplateRenderer.render(template, context)

        assert result == "User: "  # Should be empty string

    def test_render_invalid_list_index(self):
        """Test rendering with invalid list index."""
        template = "Item: {{items.5.name}}"
        context = {"items": [{"name": "Item 1"}, {"name": "Item 2"}]}

        result = TemplateRenderer.render(template, context)

        assert result == "Item: "  # Should be empty string

    def test_render_complex_variable_pattern(self):
        """Test rendering with complex variable patterns."""
        template = "{{name}} and {{name|default:\"Unknown\"}} and {{name}}"
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == "John and John and John"

    def test_render_with_whitespace_in_variables(self):
        """Test rendering with whitespace in variable definitions."""
        template = "Name: {{ name }}, Default: {{ name | default: \"Unknown\" }}"
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == "Name: John, Default: John"

    def test_render_with_special_characters_in_defaults(self):
        """Test rendering with special characters in default values."""
        template = "Value: {{value|default:\"Special: @#$%^&*()\"}}"
        context = {}

        result = TemplateRenderer.render(template, context)

        assert result == "Value: Special: @#$%^&*()"

    @patch('testmanager_app.utils.template_renderer.logger')
    def test_render_warning_for_missing_variables(self, mock_logger):
        """Test that warning is logged for missing variables without defaults."""
        template = "Hello {{missing_var}}!"
        context = {}

        result = TemplateRenderer.render(template, context)

        assert result == "Hello !"
        assert mock_logger.warning.called
        warning_call = mock_logger.warning.call_args[0][0]
        assert "模板变量未定义: missing_var" in warning_call

    @patch('testmanager_app.utils.template_renderer.logger')
    def test_render_no_warning_for_missing_variables_with_defaults(self, mock_logger):
        """Test that no warning is logged for missing variables with defaults."""
        template = "Hello {{missing_var|default:\"World\"}}!"
        context = {}

        result = TemplateRenderer.render(template, context)

        assert result == "Hello World!"
        assert not mock_logger.warning.called

    def test_get_nested_value_with_valid_path(self):
        """Test _get_nested_value method with valid path."""
        context = {
            "user": {
                "profile": {
                    "name": "John"
                }
            }
        }

        result = TemplateRenderer._get_nested_value(context, "user.profile.name")

        assert result == "John"

    def test_get_nested_value_with_list_access(self):
        """Test _get_nested_value method with list access."""
        context = {
            "items": [
                {"name": "Item 1"},
                {"name": "Item 2"}
            ]
        }

        result = TemplateRenderer._get_nested_value(context, "items.0.name")

        assert result == "Item 1"

    def test_get_nested_value_with_invalid_path(self):
        """Test _get_nested_value method with invalid path."""
        context = {"user": {"name": "John"}}

        result = TemplateRenderer._get_nested_value(context, "user.profile.name")

        assert result is None

    def test_get_nested_value_with_empty_context(self):
        """Test _get_nested_value method with empty context."""
        result = TemplateRenderer._get_nested_value({}, "user.name")

        assert result is None

    def test_get_nested_value_with_empty_path(self):
        """Test _get_nested_value method with empty path."""
        context = {"user": {"name": "John"}}

        result = TemplateRenderer._get_nested_value(context, "")

        assert result is None

    def test_get_nested_value_with_none_context(self):
        """Test _get_nested_value method with None context."""
        result = TemplateRenderer._get_nested_value(None, "user.name")

        assert result is None

    def test_get_nested_value_with_invalid_list_index(self):
        """Test _get_nested_value method with invalid list index."""
        context = {"items": [{"name": "Item 1"}]}

        result = TemplateRenderer._get_nested_value(context, "items.5.name")

        assert result is None

    def test_get_nested_value_with_non_numeric_list_index(self):
        """Test _get_nested_value method with non-numeric list index."""
        context = {"items": [{"name": "Item 1"}]}

        result = TemplateRenderer._get_nested_value(context, "items.abc.name")

        assert result is None

    def test_variable_pattern_regex(self):
        """Test the VARIABLE_PATTERN regex."""
        import re

        pattern = TemplateRenderer.VARIABLE_PATTERN

        # Test various variable formats
        test_cases = [
            ("{{name}}", ("name", None)),
            ("{{user.name}}", ("user.name", None)),
            ("{{name|default:\"John\"}}", ("name", "John")),
            ("{{user.name|default:\"Unknown\"}}", ("user.name", "Unknown")),
            ("{{ items.0.name }}", (" items.0.name ", None)),  # With whitespace
        ]

        for test_string, expected_groups in test_cases:
            match = pattern.search(test_string)
            assert match is not None
            assert match.groups() == expected_groups

    def test_render_performance_with_large_template(self):
        """Test rendering performance with large template."""
        # Create a large template with many variables
        template_parts = []
        context = {}
        for i in range(100):
            template_parts.append(f"Field{i}: {{{{value{i}}}}}")
            context[f"value{i}"] = f"Value {i}"

        template = ", ".join(template_parts)

        result = TemplateRenderer.render(template, context)

        # Verify all variables were replaced
        assert result.count("Field") == 100
        assert result.count("Value") == 100
        for i in range(100):
            assert f"Field{i}: Value {i}" in result

    def test_render_with_deeply_nested_structure(self):
        """Test rendering with deeply nested data structure."""
        template = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "{{data.level1.level2.level3.level4.value}}"
                        }
                    }
                }
            }
        }
        context = {
            "data": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "value": "Deep Value"
                            }
                        }
                    }
                }
            }
        }

        result = TemplateRenderer.render(template, context)

        expected = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "Deep Value"
                        }
                    }
                }
            }
        }
        assert result == expected

    def test_render_unicode_characters(self):
        """Test rendering with unicode characters."""
        template = "Hello {{name}}! Welcome to {{place}}!"
        context = {
            "name": "世界",
            "place": "🌍"
        }

        result = TemplateRenderer.render(template, context)

        assert result == "Hello 世界! Welcome to 🌍!"

    def test_render_mixed_quotes_in_defaults(self):
        """Test rendering with mixed quotes in default values."""
        template = 'Message: {{msg|default:"It\'s a \\"test\\" message"}}'
        context = {}

        result = TemplateRenderer.render(template, context)

        assert result == "Message: It's a \"test\" message"

    def test_render_recursive_template(self):
        """Test rendering template that contains template-like strings after rendering."""
        template = "Result: {{result}}"
        context = {"result": "Value with {{placeholder}} text"}

        result = TemplateRenderer.render(template, context)

        assert result == "Result: Value with {{placeholder}} text"  # Inner {{}} should not be processed

    def test_render_with_boolean_values(self):
        """Test rendering with boolean values."""
        template = "Enabled: {{enabled}}, Disabled: {{disabled}}"
        context = {
            "enabled": True,
            "disabled": False
        }

        result = TemplateRenderer.render(template, context)

        assert result == "Enabled: True, Disabled: False"

    def test_render_with_numeric_values(self):
        """Test rendering with numeric values."""
        template = "Integer: {{int_val}}, Float: {{float_val}}"
        context = {
            "int_val": 42,
            "float_val": 3.14159
        }

        result = TemplateRenderer.render(template, context)

        assert result == "Integer: 42, Float: 3.14159"

    def test_render_with_none_values(self):
        """Test rendering with None values."""
        template = "Value: {{value}}"
        context = {"value": None}

        result = TemplateRenderer.render(template, context)

        assert result == "Value: None"

    def test_render_empty_variable_name(self):
        """Test rendering with empty variable name in template."""
        template = "Test: {{}}"
        context = {"": "empty_key"}

        result = TemplateRenderer.render(template, context)

        assert result == "Test: empty_key"

    def test_render_with_spaces_around_braces(self):
        """Test rendering with spaces around variable braces."""
        template = "Value: {{ value }}"
        context = {"value": "test"}

        result = TemplateRenderer.render(template, context)

        assert result == "Value: test"

    def test_render_multiple_same_variables(self):
        """Test rendering template with multiple instances of same variable."""
        template = "{{name}} and {{name}} and {{name|default:\"unknown\"}}"
        context = {"name": "John"}

        result = TemplateRenderer.render(template, context)

        assert result == "John and John and John"

    def test_render_with_complex_nested_dict_and_list(self):
        """Test rendering with complex nested structure containing both dicts and lists."""
        template = {
            "config": {
                "servers": [
                    {"host": "{{servers.0.host}}", "port": "{{servers.0.port}}"},
                    {"host": "{{servers.1.host}}", "port": "{{servers.1.port|default:\"8080\"}}"}
                ],
                "database": {
                    "connection": "{{db.type}}://{{db.host}}:{{db.port}}"
                }
            }
        }
        context = {
            "servers": [
                {"host": "server1.com", "port": "3000"},
                {"host": "server2.com"}  # Missing port, should use default
            ],
            "db": {
                "type": "postgresql",
                "host": "localhost",
                "port": "5432"
            }
        }

        result = TemplateRenderer.render(template, context)

        expected = {
            "config": {
                "servers": [
                    {"host": "server1.com", "port": "3000"},
                    {"host": "server2.com", "port": "8080"}
                ],
                "database": {
                    "connection": "postgresql://localhost:5432"
                }
            }
        }
        assert result == expected