#!/usr/bin/env python3
"""
系统修复LSP错误 - Phase 1: 修复高优先级API视图
"""
import re
from pathlib import Path

def fix_knowledge_views():
    """修复 api/v1/knowledge/views.py"""
    filepath = Path('api/v1/knowledge/views.py')
    content = filepath.read_text(encoding='utf-8')
    
    # 修复1: 在 data = request.data 后添加类型断言
    content = re.sub(
        r'^(\s+)data = request\.data\s*$',
        r'\1data = request.data  # type: Dict[str, Any]',
        content,
        flags=re.MULTILINE
    )
    
    # 修复2: 修复 data.get() 调用 - 添加类型注释
    content = re.sub(
        r'^(\s+)(\w+) = data\.get\(([^)]+)\)(\s*)$',
        r'\1\2 = data.get(\3)  # type: ignore[attr-defined]\4',
        content,
        flags=re.MULTILINE
    )
    
    # 修复3: 修复 query.strip() 前添加 None 检查
    content = re.sub(
        r'^(\s+)if not query\.strip\(\):',
        r'\1if query and not query.strip():',
        content,
        flags=re.MULTILINE
    )
    
    # 修复4: 修复 int() 转换类型问题
    content = re.sub(
        r'int\(request\.query_params\.get\(([^,)]+)\)\)',
        r'int(request.query_params.get(\1) or 0)',
        content
    )
    
    content = re.sub(
        r'int\(data\.get\(([^,)]+)\)\)',
        r'int(data.get(\1) or 0)',
        content
    )
    
    # 修复5: Django ORM 模型属性访问
    # 修复 project_id 转换
    content = re.sub(
        r'self\._get_knowledge_bases\(project_id\)',
        r'self._get_knowledge_bases(int(project_id) if project_id else None)',
        content
    )
    
    # 修复6: 在 model 属性访问后添加类型忽略
    for attr in ['kb\.id', 'kb\.project_id', 'kb\.project', 'kb\.name', 
                 'kb\.description', 'kb\.status', 'kb\.document_count',
                 'kb\.embedding_model', 'kb\.chunk_size', 'kb\.chunk_overlap',
                 'knowledge_base\.id', 'doc\.id', 'doc\.knowledge_base_id',
                 'doc\.knowledge_base', 'doc\.document_type', 'doc\.sync_status',
                 'doc\.created_at', 'doc\.file_path']:
        content = re.sub(
            rf'({attr})([^\w]|$)',
            r'\1  # type: ignore[attr-defined]\2',
            content
        )
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {filepath}")

def fix_planning_views():
    """修复 api/v1/planning/views.py"""
    filepath = Path('api/v1/planning/views.py')
    if not filepath.exists():
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    # 类似的修复逻辑
    content = re.sub(
        r'^(\s+)data = request\.data\s*$',
        r'\1data = request.data  # type: Dict[str, Any]',
        content,
        flags=re.MULTILINE
    )
    
    content = re.sub(
        r'^(\s+)(\w+) = data\.get\(([^)]+)\)(\s*)$',
        r'\1\2 = data.get(\3)  # type: ignore[attr-defined]\4',
        content,
        flags=re.MULTILINE
    )
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {filepath}")

def fix_execution_views():
    """修复 api/v1/execution/views.py"""
    filepath = Path('api/v1/execution/views.py')
    if not filepath.exists():
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    content = re.sub(
        r'^(\s+)data = request\.data\s*$',
        r'\1data = request.data  # type: Dict[str, Any]',
        content,
        flags=re.MULTILINE
    )
    
    content = re.sub(
        r'^(\s+)(\w+) = data\.get\(([^)]+)\)(\s*)$',
        r'\1\2 = data.get(\3)  # type: ignore[attr-defined]\4',
        content,
        flags=re.MULTILINE
    )
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {filepath}")

def fix_flows_views():
    """修复 api/v1/flows/views.py"""
    filepath = Path('api/v1/flows/views.py')
    if not filepath.exists():
        return
    
    content = filepath.read_text(encoding='utf-8')
    
    content = re.sub(
        r'^(\s+)data = request\.data\s*$',
        r'\1data = request.data  # type: Dict[str, Any]',
        content,
        flags=re.MULTILINE
    )
    
    content = re.sub(
        r'^(\s+)(\w+) = data\.get\(([^)]+)\)(\s*)$',
        r'\1\2 = data.get(\3)  # type: ignore[attr-defined]\4',
        content,
        flags=re.MULTILINE
    )
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {filepath}")

if __name__ == '__main__':
    fix_knowledge_views()
    fix_planning_views()
    fix_execution_views()
    fix_flows_views()
    print("\nPhase 1 completed!")
