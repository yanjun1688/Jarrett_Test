import os
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ProcessPRDView(View):
    """处理PRD文档并生成测试用例的视图"""
    
    def post(self, request):
        """处理POST请求，接收PRD文档并生成测试用例"""
        try:
            # 检查是否有文件上传
            if 'file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No file provided'
                }, status=400)
            
            # 获取API Key（从请求参数或表单数据中获取）
            api_key = request.POST.get('api_key') or request.GET.get('api_key')
            if not api_key:
                return JsonResponse({
                    'success': False,
                    'error': 'API Key is required'
                }, status=400)
            
            # 获取上传的文件
            uploaded_file = request.FILES['file']
            
            # 保存文件到临时位置
            temp_file_path = f"temp_{uploaded_file.name}"
            with open(temp_file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # 处理文档，传入API Key
            result = self.process_document(temp_file_path, api_key)
            
            # 清理临时文件
            os.remove(temp_file_path)
            
            return JsonResponse({
                'success': True,
                'message': 'Test cases generated successfully',
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error processing PRD document: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def process_document(self, file_path, api_key):
        """处理文档并生成测试用例"""
        # 延迟导入，避免在模块级别执行任何代码（Celery兼容性）
        from .document_loader import DocumentLoader
        from .ai_processor import AIProcessor
        
        # 初始化处理器，传入API Key
        document_loader = DocumentLoader()
        ai_processor = AIProcessor(api_key=api_key)
        
        # 加载文档
        content = document_loader.load_document(file_path)
        
        # 处理文档内容（这里简化为整个文档作为一个块）
        processed_chunk = ai_processor.process_prd_chunk("chunk_1", content)
        
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

