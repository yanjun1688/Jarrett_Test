"""
Prompt builder for test code generation
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FrameworkConfig:
    """Framework configuration for code generation"""
    name: str
    import_style: str = ""
    test_function_pattern: str = ""
    assertion_style: str = ""
    fixture_support: bool = False
    language: str = "python"


class PromptBuilder:
    """Builds prompts for test code generation"""
    
    @staticmethod
    def build_generation_prompt(
        test_case: Dict[str, Any],
        framework: str,
        framework_config: Optional[Dict[str, Any]] = None,
        style_info: Optional[Dict[str, Any]] = None,
        pattern_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build code generation prompt
        
        Args:
            test_case: Test case dictionary
            framework: Test framework name
            framework_config: Framework configuration
            style_info: Code style information
            pattern_info: Common patterns in project
            
        Returns:
            Prompt text
        """
        prompt_parts = []
        
        # Test case information
        prompt_parts.append("## Test Case")
        prompt_parts.append(f"Name: {test_case.get('name', 'Unknown')}")
        prompt_parts.append(f"Description: {test_case.get('description', '')}")
        prompt_parts.append(f"Priority: {test_case.get('priority', 'Medium')}")
        
        # Test steps
        steps = test_case.get('steps', [])
        if steps:
            prompt_parts.append("\n## Test Steps")
            for i, step in enumerate(steps, 1):
                prompt_parts.append(f"{i}. {step}")
        
        # Expected result
        expected = test_case.get('expected_result', '')
        if expected:
            prompt_parts.append(f"\n## Expected Result\n{expected}")
        
        # Framework and style guidelines
        prompt_parts.append("\n## Code Style Guidelines")
        prompt_parts.append(f"Test Framework: {framework}")
        
        if framework_config:
            import_style = framework_config.get('import_style', '')
            test_pattern = framework_config.get('test_function_pattern', '')
            assertion_style = framework_config.get('assertion_style', '')
            
            if import_style:
                prompt_parts.append(f"Import Style: {import_style}")
            if test_pattern:
                prompt_parts.append(f"Test Function Pattern: {test_pattern}")
            if assertion_style:
                prompt_parts.append(f"Assertion Style: {assertion_style}")
            
            if framework_config.get('fixture_support'):
                prompt_parts.append("Fixtures: Use fixtures for test data setup if applicable")
        
        # Style information
        if style_info:
            common_patterns = style_info.get('common_patterns', [])
            if common_patterns:
                prompt_parts.append("\n## Common Patterns")
                for pattern in common_patterns[:3]:
                    prompt_parts.append(f"- {pattern.get('type', '')}: {pattern.get('description', '')}")
        
        # Common patterns in project
        if pattern_info:
            common_patterns = pattern_info.get('common_patterns', [])
            if common_patterns:
                prompt_parts.append("\n## Common Patterns in Project")
                for pattern in common_patterns[:3]:
                    prompt_parts.append(f"- {pattern.get('type', '')}: {pattern.get('description', '')}")
        
        # Output requirements
        prompt_parts.append("\n## Output Requirements")
        prompt_parts.append("1. Generate complete, executable test code")
        prompt_parts.append("2. Follow the project's coding style and patterns")
        prompt_parts.append("3. Include appropriate imports and setup")
        prompt_parts.append("4. Add meaningful comments")
        prompt_parts.append("5. Include error handling where appropriate")
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def get_system_message(framework: str) -> str:
        """Get system message for specific framework"""
        framework_messages = {
            'pytest': """You are an expert Python testing engineer using pytest. 
Generate high-quality pytest test code that follows best practices:
- Use pytest fixtures for setup/teardown
- Use descriptive test names
- Use appropriate assertions
- Include docstrings
- Handle exceptions properly""",
            
            'unittest': """You are an expert Python testing engineer using unittest.
Generate high-quality unittest test code that follows best practices:
- Use unittest.TestCase class structure
- Use setUp/tearDown methods
- Use descriptive test method names
- Include docstrings
- Handle exceptions properly""",
            
            'jest': """You are an expert JavaScript testing engineer using Jest.
Generate high-quality Jest test code that follows best practices:
- Use descriptive test names
- Use appropriate matchers
- Include setup/teardown
- Mock dependencies properly
- Handle async code correctly""",
            
            'mocha': """You are an expert JavaScript testing engineer using Mocha.
Generate high-quality Mocha test code that follows best practices:
- Use descriptive test names
- Use appropriate assertions (Chai)
- Include before/after hooks
- Handle async code correctly"""
        }
        
        return framework_messages.get(framework, """You are an expert testing engineer.
Generate high-quality test code that follows best practices for the specified framework.""")