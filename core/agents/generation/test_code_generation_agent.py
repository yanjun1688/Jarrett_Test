"""
Test code generation agent
"""

from typing import Dict, Any, Optional, List
import logging
from asgiref.sync import sync_to_async
import json

from core.agents.base_agent import BaseAgent
from core.agents.generation.prompt_builder import PromptBuilder
from core.agents.generation.code_quality_validator import CodeQualityValidator
from shared.exceptions import (
    ValidationError,
    ConfigurationError,
    ExternalServiceError,
    CodeGenerationError
)
from shared.utils.validation import validate_required_fields

logger = logging.getLogger(__name__)


class TestCodeGenerationAgent(BaseAgent):
    """Test code generation agent"""
    
    def __init__(
        self,
        llm_service: Optional[Any] = None,
        rag_retriever: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize code generation agent
        
        Args:
            llm_service: LLM service (optional)
            rag_retriever: RAG retriever (optional)
            config: Agent configuration
        """
        super().__init__(config=config)
        
        self.llm_service = llm_service
        self.rag_retriever = rag_retriever
        
        # Initialize components
        self.prompt_builder = PromptBuilder()
        self.quality_validator = CodeQualityValidator()
        
        # Analyzers (lazy initialization)
        self.project_analyzer = None
        self.style_analyzer = None
        self.pattern_analyzer = None
        
        logger.info("TestCodeGenerationAgent initialized")
    
    async def initialize(self) -> None:
        """
        初始化Agent
        
        加载必要的资源和配置
        """
        logger.info(f"TestCodeGenerationAgent {self.agent_id} initialized")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Agent的主要功能
        
        Args:
            input_data: 输入数据，包含test_case等信息
            
        Returns:
            执行结果
        """
        test_case = input_data.get('test_case')
        if not test_case:
            raise ValidationError("test_case is required in input_data")
        
        framework = input_data.get('framework', 'pytest')
        language = input_data.get('language', 'python')
        project_path = input_data.get('project_path')
        
        return await self.generate_test_code(
            test_case=test_case,
            framework=framework,
            language=language,
            project_path=project_path
        )
    
    async def cleanup(self) -> None:
        """
        清理资源
        
        释放Agent持有的资源
        """
        self.llm_service = None
        self.rag_retriever = None
        logger.info(f"TestCodeGenerationAgent {self.agent_id} cleaned up")
    
    def _create_llm_copy(self) -> Optional[Any]:
        """
        Create a copy of LLM service for parallel execution
        
        Returns:
            New LLM service instance with same configuration
        """
        if not self.llm_service:
            return None
        
        try:
            from core.agents.llm.base_llm import create_llm_service, LLMProvider
            
            config = self.llm_service.config
            return create_llm_service(
                provider=config.provider.value,
                model_name=config.model_name,
                api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                **config.extra_params
            )
        except Exception as e:
            logger.warning(f"Failed to create LLM copy: {e}, using original service")
            return self.llm_service
    
    async def generate_test_code(
        self,
        test_case: Dict[str, Any],
        framework: str = 'pytest',
        language: str = 'python',
        project_path: Optional[str] = None,
        validate_quality: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate test code from test case
        
        Args:
            test_case: Test case dictionary
            framework: Test framework
            language: Programming language
            project_path: Path to project for analysis
            validate_quality: Whether to validate code quality
            max_retries: Maximum retry attempts
            
        Returns:
            Dictionary with generated code and metadata
        """
        try:
            # Validate input
            self._validate_test_case(test_case)
            
            # Update agent status
            self.update_state('analyzing', **{
                'test_case': test_case.get('name', 'unknown'),
                'framework': framework,
                'language': language
            })
            
            # Analyze project if path provided
            project_info = {}
            if project_path:
                project_info = await self._analyze_project(project_path)
            
            # Generate code with retry logic
            generated_code = None
            quality_result = None
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Generating test code (attempt {attempt + 1}/{max_retries})")
                    
                    # Build prompt
                    prompt = self.prompt_builder.build_generation_prompt(
                        test_case=test_case,
                        framework=framework,
                        framework_config=self._get_framework_config(framework, language),
                        style_info=project_info.get('style', {}),
                        pattern_info=project_info.get('patterns', {})
                    )
                    
                    # Get system message
                    system_message = self.prompt_builder.get_system_message(framework)
                    
                    # Generate code using LLM
                    generated_code = await self._generate_with_llm(
                        prompt=prompt,
                        system_message=system_message,
                        language=language
                    )
                    
                    # Validate code quality
                    if validate_quality and generated_code:
                        quality_result = self.quality_validator.validate_code_quality(
                            code=generated_code,
                            language=language,
                            framework=framework
                        )
                        
                        if not quality_result['passed']:
                            logger.warning(f"Code quality issues found: {quality_result['summary']}")
                            
                            if quality_result['score'] < 70:
                                if attempt < max_retries - 1:
                                    prompt = self._enhance_prompt_with_feedback(
                                        original_prompt=prompt,
                                        quality_issues=quality_result['issues']
                                    )
                                    continue
                                else:
                                    raise CodeGenerationError(
                                        f"Failed to generate test code after {max_retries} attempts: "
                                        f"quality score {quality_result['score']} is below threshold (70)"
                                    )
                    
                    # If we get here, generation was successful
                    break
                    
                except CodeGenerationError:
                    raise
                    
                except Exception as e:
                    logger.error(f"Generation attempt {attempt + 1} failed: {str(e)}")
                    
                    if attempt == max_retries - 1:
                        raise CodeGenerationError(
                            f"Failed to generate test code after {max_retries} attempts: {str(e)}"
                        )
            
            # Build result
            result = {
                'code': generated_code,
                'test_case': test_case,
                'framework': framework,
                'language': language,
                'quality_score': quality_result['score'] if quality_result else None,
                'quality_issues': quality_result['issues'] if quality_result else [],
                'metadata': {
                    'generation_time': self.get_execution_time(),
                    'attempts': attempt + 1 if 'attempt' in locals() else 1
                }
            }
            
            # Update agent status
            self.update_state('completed', **{
                'result': 'success',
                'quality_score': result['quality_score']
            })
            
            logger.info(f"Test code generated successfully (quality score: {result['quality_score']})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate test code: {str(e)}")
            self.update_state('failed', **{'error': str(e)})
            raise
    
    async def generate_multiple_tests(
        self,
        test_cases: List[Dict[str, Any]],
        framework: str = 'pytest',
        language: str = 'python',
        project_path: Optional[str] = None,
        parallel: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple test codes
        
        Args:
            test_cases: List of test cases
            framework: Test framework
            language: Programming language
            project_path: Path to project for analysis
            parallel: Whether to generate in parallel
            
        Returns:
            List of generation results
        """
        results = []
        
        if parallel:
            import asyncio
            from core.agents.llm.base_llm import create_llm_service
            
            tasks = []
            
            for test_case in test_cases:
                agent_copy = TestCodeGenerationAgent(
                    llm_service=self._create_llm_copy() if self.llm_service else None,
                    rag_retriever=self.rag_retriever,
                    config=self.config
                )
                task = agent_copy.generate_test_code(
                    test_case=test_case,
                    framework=framework,
                    language=language,
                    project_path=project_path,
                    validate_quality=True
                )
                tasks.append(task)
            
            results_raw = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            for i, result in enumerate(results_raw):
                if isinstance(result, Exception):
                    logger.error(f"Failed to generate test for case {i}: {str(result)}")
                    results.append({
                        'code': None,
                        'test_case': test_cases[i],
                        'error': str(result),
                        'success': False
                    })
                else:
                    results.append(result)
        else:
            # Sequential generation
            for i, test_case in enumerate(test_cases):
                try:
                    logger.info(f"Generating test {i + 1}/{len(test_cases)}")
                    
                    result = await self.generate_test_code(
                        test_case=test_case,
                        framework=framework,
                        language=language,
                        project_path=project_path,
                        validate_quality=True
                    )
                    result['success'] = True
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Failed to generate test for case {i}: {str(e)}")
                    results.append({
                        'code': None,
                        'test_case': test_case,
                        'error': str(e),
                        'success': False
                    })
        
        return results
    
    def _validate_test_case(self, test_case: Dict[str, Any]) -> None:
        """Validate test case structure"""
        required_fields = ['name', 'steps']
        
        missing_fields = validate_required_fields(test_case, required_fields)
        if missing_fields:
            raise ValidationError(f"Invalid test case: missing fields: {', '.join(missing_fields)}")
        
        # Validate steps
        steps = test_case.get('steps', [])
        if not isinstance(steps, list) or len(steps) == 0:
            raise ValidationError("Test case must have at least one step")
        
        # Validate step format
        for i, step in enumerate(steps):
            if not isinstance(step, str) or not step.strip():
                raise ValidationError(f"Step {i + 1} must be a non-empty string")
    
    async def _analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze project for code style and patterns"""
        logger.warning("Project analysis unavailable: legacy framework has been removed, migration in progress")
        return {}
    
    def _get_framework_config(
        self,
        framework: str,
        language: str
    ) -> Dict[str, Any]:
        """Get framework configuration"""
        framework_configs = {
            'pytest': {
                'import_style': 'import pytest',
                'test_function_pattern': 'def test_',
                'assertion_style': 'assert',
                'fixture_support': True,
                'language': 'python'
            },
            'unittest': {
                'import_style': 'import unittest',
                'test_function_pattern': 'def test_',
                'assertion_style': 'self.assert',
                'fixture_support': False,
                'language': 'python'
            },
            'jest': {
                'import_style': "import { describe, it, expect } from '@jest/globals'",
                'test_function_pattern': 'it(',
                'assertion_style': 'expect(',
                'fixture_support': True,
                'language': 'javascript'
            },
            'mocha': {
                'import_style': "const { describe, it } = require('mocha')",
                'test_function_pattern': 'it(',
                'assertion_style': 'assert.',
                'fixture_support': True,
                'language': 'javascript'
            }
        }
        
        config = framework_configs.get(framework, {}).copy()
        
        if language and language != config.get('language'):
            config['language'] = language
        
        return config
    
    async def _generate_with_llm(
        self,
        prompt: str,
        system_message: str,
        language: str
    ) -> str:
        """Generate code using LLM service"""
        if not self.llm_service:
            raise ConfigurationError("LLM service is required for code generation")
        
        try:
            # Generate code using BaseLLMService.generate(prompt, system_message, ...) signature
            response = await self.llm_service.generate(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,  # Low temperature for consistent code
                max_tokens=2000
            )
            
            # Extract code from response
            generated_code = self._extract_code_from_response(response, language)
            
            if not generated_code:
                raise CodeGenerationError("Failed to extract code from LLM response")
            
            return generated_code
            
        except Exception as e:
            raise CodeGenerationError(f"LLM generation failed: {str(e)}")
    
    def _extract_code_from_response(self, response: str, language: str) -> str:
        """Extract code from LLM response"""
        # Try to find code blocks
        code_blocks = []
        
        # Look for markdown code blocks
        import re
        pattern = fr'```{language}?\s*(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            code_blocks.extend(matches)
        
        # If no code blocks found, try to extract indented code
        if not code_blocks:
            lines = response.split('\n')
            code_lines = []
            in_code = False
            
            for line in lines:
                # Check if line looks like code (starts with import, def, class, etc.)
                if (line.strip().startswith(('import ', 'from ', 'def ', 'class ', 'it(', 'describe(', 'test(')) or
                    (language == 'python' and line.strip().startswith('@')) or
                    (language == 'javascript' and line.strip().startswith(('const ', 'let ', 'var ', 'function ')))):
                    in_code = True
                
                if in_code:
                    code_lines.append(line)
            
            if code_lines:
                code_blocks.append('\n'.join(code_lines))
        
        # Return the first code block or the entire response
        if code_blocks:
            return code_blocks[0].strip()
        else:
            # Clean up the response
            lines = response.split('\n')
            # Remove lines that are clearly not code (explanations, etc.)
            code_lines = [line for line in lines if not line.strip().startswith(('# ', '// ', '/*', '* '))]
            return '\n'.join(code_lines).strip()
    
    def _enhance_prompt_with_feedback(
        self,
        original_prompt: str,
        quality_issues: List[Dict[str, Any]]
    ) -> str:
        """Enhance prompt with quality feedback"""
        feedback_lines = ["\n## Quality Feedback from Previous Attempt"]
        
        # Group issues by severity
        errors = [issue for issue in quality_issues if issue['severity'] == 'error']
        warnings = [issue for issue in quality_issues if issue['severity'] == 'warning']
        
        if errors:
            feedback_lines.append("\nCritical issues to fix:")
            for error in errors[:3]:  # Limit to top 3 errors
                feedback_lines.append(f"- {error['message']}")
                if error.get('suggestion'):
                    feedback_lines.append(f"  Suggestion: {error['suggestion']}")
        
        if warnings:
            feedback_lines.append("\nImprovements to consider:")
            for warning in warnings[:3]:  # Limit to top 3 warnings
                feedback_lines.append(f"- {warning['message']}")
                if warning.get('suggestion'):
                    feedback_lines.append(f"  Suggestion: {warning['suggestion']}")
        
        feedback = "\n".join(feedback_lines)
        
        # Add instructions for improvement
        improvement_instructions = """
        
## Instructions for Improvement
Please regenerate the test code addressing the issues mentioned above.
Ensure the new code:
1. Fixes all critical errors
2. Addresses major warnings
3. Follows best practices more closely
4. Maintains readability and maintainability
"""
        
        return original_prompt + feedback + improvement_instructions