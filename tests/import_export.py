import pandas as pd
import openpyxl
from io import BytesIO
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import TestCase, Project, Module
from .serializers import TestCaseSerializer


@api_view(['POST'])
def import_testcases(request):
    """导入测试用例（Excel/CSV）"""
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    project_id = request.data.get('project_id')
    
    if not project_id:
        return Response({'error': 'project_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # 读取文件
        if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
            df = pd.read_excel(file)
        elif file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            return Response({'error': 'Unsupported file format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证必要列
        required_columns = ['title', 'module_name', 'steps', 'expected_result']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return Response(
                {'error': f'Missing required columns: {missing_columns}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 获取或创建模块
                module_name = row['module_name']
                module, created = Module.objects.get_or_create(
                    project=project,
                    name=module_name,
                    defaults={'description': f'自动创建的模块：{module_name}'}
                )
                
                # 创建测试用例
                testcase = TestCase.objects.create(
                    title=row['title'],
                    project=project,
                    module=module,
                    priority=row.get('priority', 'medium'),
                    precondition=row.get('precondition', ''),
                    steps=row['steps'],
                    expected_result=row['expected_result'],
                    created_by=request.user if request.user.is_authenticated else None
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f'Row {index + 2}: {str(e)}')
        
        return Response({
            'message': f'Successfully imported {created_count} test cases',
            'created_count': created_count,
            'errors': errors
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def export_testcases(request):
    """导出测试用例（Excel）"""
    project_id = request.query_params.get('project_id')
    
    if not project_id:
        return Response({'error': 'project_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # 获取测试用例数据
    testcases = TestCase.objects.filter(project=project).select_related('module', 'created_by')
    
    # 准备数据
    data = []
    for testcase in testcases:
        data.append({
            'ID': testcase.id,
            'title': testcase.title,
            'module_name': testcase.module.name,
            'priority': testcase.get_priority_display(),
            'precondition': testcase.precondition,
            'steps': testcase.steps,
            'expected_result': testcase.expected_result,
            'created_by': testcase.created_by.username if testcase.created_by else '',
            'created_at': testcase.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 创建Excel文件
    df = pd.DataFrame(data)
    
    # 创建BytesIO对象
    output = BytesIO()
    
    # 使用openpyxl引擎写入Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='TestCases', index=False)
    
    # 准备响应
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{project.name}_testcases.xlsx"'
    
    return response


@api_view(['GET'])
def get_import_template(request):
    """获取导入模板"""
    # 创建模板数据
    template_data = [
        {
            'title': '示例测试用例1',
            'module_name': '登录模块',
            'priority': 'high',
            'precondition': '用户已注册',
            'steps': '1. 打开登录页面\n2. 输入用户名和密码\n3. 点击登录按钮',
            'expected_result': '登录成功，跳转到首页'
        },
        {
            'title': '示例测试用例2',
            'module_name': '商品管理',
            'priority': 'medium',
            'precondition': '用户已登录',
            'steps': '1. 进入商品列表\n2. 点击添加商品\n3. 填写商品信息\n4. 保存',
            'expected_result': '商品添加成功'
        }
    ]
    
    df = pd.DataFrame(template_data)
    
    # 创建BytesIO对象
    output = BytesIO()
    
    # 使用openpyxl引擎写入Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Template', index=False)
    
    # 准备响应
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="testcase_import_template.xlsx"'
    
    return response