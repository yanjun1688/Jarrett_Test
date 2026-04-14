"""
Code quality validator for generated test code
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class QualityIssue:
    """Code quality issue"""
    severity: str  # 'error', 'warning', 'info'
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


class CodeQualityValidator:
    """Validates code quality for generated test code"""
    
    def __init__(self):
        self.quality_rules = self._initialize_quality_rules()
    
    def _initialize_quality_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize quality validation rules"""
        return {
            'python': {
                'imports': {
                    'pattern': r'^import\s+|^from\s+',
                    'required': ['import', 'from'],
                    'forbidden': ['import *']
                },
                'test_functions': {
                    'pattern': r'def\s+test_',
                    'required': True
                },
                'assertions': {
                    'pattern': r'assert\s+',
                    'required': True
                },
                'docstrings': {
                    'pattern': r'""".*?"""|\'\'\'.*?\'\'\'',
                    'required': True
                }
            },
            'javascript': {
                'imports': {
                    'pattern': r'^import\s+|^const\s+|^let\s+|^var\s+',
                    'required': ['import', 'require'],
                    'forbidden': []
                },
                'test_functions': {
                    'pattern': r'it\(|test\(|describe\(',
                    'required': True
                },
                'assertions': {
                    'pattern': r'expect\(|assert\.',
                    'required': True
                }
            }
        }
    
    def validate_code_quality(
        self,
        code: str,
        language: str = 'python',
        framework: str = 'pytest'
    ) -> Dict[str, Any]:
        """
        Validate code quality
        
        Args:
            code: Generated code to validate
            language: Programming language
            framework: Test framework
            
        Returns:
            Validation results with issues and score
        """
        issues: List[QualityIssue] = []
        
        # Basic syntax checks
        if not code.strip():
            return {
                'score': 0,
                'issues': [{
                    'severity': 'error',
                    'message': 'Generated code is empty',
                    'line': None,
                    'suggestion': 'Generated code cannot be empty'
                }],
                'summary': {
                    'total_issues': 1,
                    'errors': 1,
                    'warnings': 0,
                    'info': 0
                },
                'passed': False
            }
        
        # Language-specific validation
        if language in self.quality_rules:
            issues.extend(self._validate_language_specific(code, language, framework))
        
        # Framework-specific validation
        issues.extend(self._validate_framework_specific(code, framework))
        
        # General code quality checks
        issues.extend(self._validate_general_quality(code))
        
        return self._build_validation_result(issues)
    
    def _validate_language_specific(
        self,
        code: str,
        language: str,
        framework: str
    ) -> List[QualityIssue]:
        """Validate language-specific rules"""
        issues = []
        rules = self.quality_rules.get(language, {})
        
        lines = code.split('\n')
        
        # Check imports
        if 'imports' in rules:
            import_rules = rules['imports']
            import_pattern = import_rules.get('pattern', '')
            required_imports = import_rules.get('required', [])
            forbidden_imports = import_rules.get('forbidden', [])
            
            has_imports = any(re.search(import_pattern, line) for line in lines)
            
            if required_imports and not has_imports:
                issues.append(QualityIssue(
                    severity='warning',
                    message=f'No imports found. Consider adding imports for {framework}',
                    suggestion=f'Add import statements for {framework}'
                ))
            
            # Check for forbidden imports
            for forbidden in forbidden_imports:
                if any(forbidden in line for line in lines):
                    issues.append(QualityIssue(
                        severity='warning',
                        message=f'Found potentially problematic import: {forbidden}',
                        suggestion='Avoid wildcard imports'
                    ))
        
        # Check test functions
        if 'test_functions' in rules:
            test_func_rules = rules['test_functions']
            test_pattern = test_func_rules.get('pattern', '')
            required = test_func_rules.get('required', False)
            
            has_test_funcs = any(re.search(test_pattern, line) for line in lines)
            
            if required and not has_test_funcs:
                issues.append(QualityIssue(
                    severity='error',
                    message='No test functions found',
                    suggestion=f'Add test functions using {framework} patterns'
                ))
        
        # Check assertions
        if 'assertions' in rules:
            assertion_rules = rules['assertions']
            assertion_pattern = assertion_rules.get('pattern', '')
            required = assertion_rules.get('required', False)
            
            has_assertions = any(re.search(assertion_pattern, line) for line in lines)
            
            if required and not has_assertions:
                issues.append(QualityIssue(
                    severity='error',
                    message='No assertions found in test code',
                    suggestion='Add assertions to verify test results'
                ))
        
        # Check docstrings
        if 'docstrings' in rules:
            docstring_rules = rules['docstrings']
            docstring_pattern = docstring_rules.get('pattern', '')
            required = docstring_rules.get('required', False)
            
            has_docstrings = bool(re.search(docstring_pattern, code, re.DOTALL))
            
            if required and not has_docstrings:
                issues.append(QualityIssue(
                    severity='warning',
                    message='No docstrings found',
                    suggestion='Add docstrings to describe test purpose'
                ))
        
        return issues
    
    def _validate_framework_specific(
        self,
        code: str,
        framework: str
    ) -> List[QualityIssue]:
        """Validate framework-specific patterns"""
        issues = []
        
        framework_patterns = {
            'pytest': [
                (r'@pytest\.fixture', 'Consider using pytest fixtures for setup'),
                (r'def test_', 'Test functions should start with "test_"'),
                (r'assert ', 'Use pytest assertions')
            ],
            'unittest': [
                (r'class.*TestCase', 'Test classes should inherit from TestCase'),
                (r'def test_', 'Test methods should start with "test_"'),
                (r'self\.assert', 'Use unittest assertions')
            ],
            'jest': [
                (r'describe\(', 'Use describe blocks to group tests'),
                (r'it\(|test\(', 'Use it() or test() for individual tests'),
                (r'expect\(', 'Use expect() for assertions')
            ],
            'mocha': [
                (r'describe\(', 'Use describe blocks to group tests'),
                (r'it\(', 'Use it() for individual tests'),
                (r'assert\.', 'Use assertion library (Chai)')
            ]
        }
        
        patterns = framework_patterns.get(framework, [])
        for pattern, suggestion in patterns:
            if not re.search(pattern, code):
                issues.append(QualityIssue(
                    severity='info',
                    message=f'Missing {framework} pattern: {pattern}',
                    suggestion=suggestion
                ))
        
        return issues
    
    def _validate_general_quality(self, code: str) -> List[QualityIssue]:
        """Validate general code quality"""
        issues = []
        lines = code.split('\n')
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # PEP 8 recommends 79, but 100 is more practical
                issues.append(QualityIssue(
                    severity='warning',
                    message=f'Line {i} exceeds 100 characters ({len(line)} chars)',
                    line=i,
                    suggestion='Break long lines for better readability'
                ))
        
        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                issues.append(QualityIssue(
                    severity='info',
                    message=f'Line {i} contains TODO/FIXME comment',
                    line=i,
                    suggestion='Address TODO/FIXME comments before production'
                ))
        
        # Check for print statements (debug code)
        for i, line in enumerate(lines, 1):
            if re.search(r'print\(|console\.log', line):
                issues.append(QualityIssue(
                    severity='warning',
                    message=f'Line {i} contains print/console.log statement',
                    line=i,
                    suggestion='Remove debug statements from production code'
                ))
        
        return issues
    
    def _build_validation_result(
        self,
        issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """Build validation result dictionary"""
        error_count = sum(1 for issue in issues if issue.severity == 'error')
        warning_count = sum(1 for issue in issues if issue.severity == 'warning')
        info_count = sum(1 for issue in issues if issue.severity == 'info')
        
        total_issues = len(issues)
        score = max(0, 100 - (error_count * 10 + warning_count * 5 + info_count * 2))
        
        return {
            'score': score,
            'issues': [
                {
                    'severity': issue.severity,
                    'message': issue.message,
                    'line': issue.line,
                    'suggestion': issue.suggestion
                }
                for issue in issues
            ],
            'summary': {
                'total_issues': total_issues,
                'errors': error_count,
                'warnings': warning_count,
                'info': info_count
            },
            'passed': error_count == 0
        }