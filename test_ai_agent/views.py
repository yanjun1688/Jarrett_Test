import os
import logging
import asyncio
import tempfile
from typing import Any, TYPE_CHECKING, cast
from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict

from rest_framework.request import Request
from django.http import JsonResponse
from django.utils.text import get_valid_filename
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from asgiref.sync import sync_to_async, async_to_sync

logger = logging.getLogger(__name__)

_MAX_UPLOAD_SIZE = 10 * 1024 * 1024
_ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.doc'}


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return None


class ProcessPRDView(APIView):
    """处理PRD文档并生成测试用例的视图"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request: Request) -> JsonResponse:
        """处理POST请求，接收PRD文档并生成测试用例"""
        try:
            # 类型断言：明确FILES的类型
            files = cast(MultiValueDict[str, UploadedFile], request.FILES)
            
            # 检查是否有文件上传
            if 'file' not in files:
                return JsonResponse({
                    'success': False,
                    'error': 'No file provided'
                }, status=400)

            # 获取上传的文件
            uploaded_file = files['file']
            # 类型守卫：确保uploaded_file是UploadedFile类型（不是列表）
            if isinstance(uploaded_file, list):
                uploaded_file = uploaded_file[0] if uploaded_file else None
            if not isinstance(uploaded_file, UploadedFile):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid file format'
                }, status=400)
            
            # 添加类型断言
            assert uploaded_file.size is not None, "File size cannot be None"
            assert uploaded_file.name is not None and uploaded_file.name != "", "File name cannot be empty"

            # 文件大小限制
            if uploaded_file.size is None:
                return JsonResponse({  # type: ignore[unreachable]
                    'success': False,
                    'error': 'Invalid file: size is None'
                }, status=400)
            if uploaded_file.size > _MAX_UPLOAD_SIZE:
                return JsonResponse({
                    'success': False,
                    'error': f'File too large. Maximum size is {_MAX_UPLOAD_SIZE // (1024*1024)}MB'
                }, status=400)

            # 文件类型限制
            if not uploaded_file.name:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid file: name is empty'
                }, status=400)
            safe_name = get_valid_filename(uploaded_file.name)
            ext = os.path.splitext(safe_name)[1].lower()
            if ext not in _ALLOWED_EXTENSIONS:
                return JsonResponse({
                    'success': False,
                    'error': f'File type not allowed. Allowed: {", ".join(_ALLOWED_EXTENSIONS)}'
                }, status=400)

            # 使用安全的临时文件
            fd, temp_file_path = tempfile.mkstemp(suffix=ext)
            try:
                with os.fdopen(fd, 'wb') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

                # 处理文档，使用默认配置的 Qwen 模型
                result = async_to_sync(self.process_document)(temp_file_path)
            finally:
                # 确保临时文件被清理
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

            return JsonResponse({
                'success': True,
                'message': 'Test cases generated successfully',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error processing PRD document: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': '服务器内部错误'
            }, status=500)
    
    async def process_document(self, file_path):
        """处理文档并生成测试用例"""
        # 延迟导入，避免在模块级别执行任何代码（Celery兼容性）
        from .document_loader import DocumentLoader
        from .ai_processor import AIProcessor

        # 初始化处理器，使用默认配置
        document_loader = DocumentLoader()
        ai_processor = AIProcessor()
        
        # 加载文档
        content = document_loader.load_document(file_path)
        
        # 处理文档内容（这里简化为整个文档作为一个块）
        processed_chunk = await ai_processor.process_prd_chunk("chunk_1", content)
        
        # 将Pydantic模型转换为字典，以便JSON序列化
        test_suites_data = []
        for suite in processed_chunk.test_suites:
            test_cases_data = []
            for case in suite.test_cases:
                test_cases_data.append({
                    'title': case.title,
                    'description': case.description,
                    'preconditions': case.preconditions,
                    'steps': case.steps,
                    'expected_result': case.expected_result,
                    'priority': case.priority,
                    'type': case.type,
                    'category': case.category
                })
            test_suites_data.append({
                'name': suite.name,
                'description': suite.description,
                'test_cases': test_cases_data
            })
        
        # 返回处理结果（包含完整的test_suites数据）
        return {
            'chunk_id': processed_chunk.chunk_id,
            'test_suites_count': len(processed_chunk.test_suites),
            'test_suites': test_suites_data
        }

