#!/usr/bin/env python
"""
检查测试用例相关表的数据情况
用于诊断数据分散和模型使用问题
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from django.db import connection
from django.utils import timezone


def print_separator(title: str) -> None:
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_row(*columns: str, widths: list[int] | None = None) -> None:
    """打印一行数据"""
    if widths is None:
        widths = [30, 20, 20, 20, 20]
    row = ""
    for i, col in enumerate(columns):
        w = widths[i] if i < len(widths) else 20
        row += str(col)[:w].ljust(w)
    print(row)


def check_table_counts() -> None:
    """检查各表的数据量"""
    print_separator("各表数据量统计")
    
    tables = [
        ("core_test_case", "TestCase (core)"),
        ("feature_test_case", "FeatureTestCase"),
        ("test_script", "TestScript"),
        ("api_request", "ApiRequest"),
        ("api_assertion", "ApiAssertion"),
        ("test_execution", "TestExecution"),
    ]
    
    print(f"{'表名':<25} {'说明':<25} {'数据量':<10}")
    print("-" * 60)
    
    for table_name, description in tables:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
            print(f"{table_name:<25} {description:<25} {count:<10}")
        except Exception as e:
            print(f"{table_name:<25} {description:<25} 错误: {e}")


def check_core_test_case() -> None:
    """TestCase 模型已删除"""
    print_separator("core_test_case 表 (已迁移)")
    print("TestCase 模型已删除，功能测试用例已统一迁移到 FeatureTestCase 模型")


def check_feature_test_case() -> None:
    """检查 feature_test_case 表"""
    print_separator("feature_test_case 表详情 (FeatureTestCase)")
    
    from testmanager_app.models import FeatureTestCase
    
    cases = FeatureTestCase.objects.all().order_by('-created_at')[:20]
    
    if not cases:
        print("无数据")
        return
    
    print(f"总数据量: {FeatureTestCase.objects.count()}")
    print()
    print(f"{'ID':<6} {'标题':<40} {'预期结果':<20} {'创建时间':<20}")
    print("-" * 90)
    
    for tc in cases:
        created = tc.created_at.strftime('%Y-%m-%d %H:%M') if tc.created_at else '-'
        expected = (tc.expected_result[:18] + '...') if len(tc.expected_result) > 20 else tc.expected_result
        expected = expected or '(空)'
        print(f"{tc.id:<6} {tc.title[:38]:<40} {expected:<20} {created:<20}")
    
    # 检查 expected_result 为空的情况
    empty_count = FeatureTestCase.objects.filter(expected_result='').count()
    print(f"\n预期结果为空的记录数: {empty_count}")


def check_test_script() -> None:
    """检查 test_script 表"""
    print_separator("test_script 表详情 (TestScript)")
    
    from testmanager_app.models import TestScript
    
    scripts = TestScript.objects.all().order_by('-created_at')[:20]
    
    if not scripts:
        print("无数据")
        return
    
    print(f"总数据量: {TestScript.objects.count()}")
    print()
    print(f"{'ID':<6} {'来源':<15} {'类型':<10} {'名称':<35} {'创建时间':<20}")
    print("-" * 90)
    
    for s in scripts:
        created = s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '-'
        print(f"{s.id:<6} {s.source:<15} {s.script_type:<10} {s.name[:33]:<35} {created:<20}")
    
    # 统计来源分布
    print("\n来源分布:")
    source_stats = TestScript.objects.values('source').annotate(
        count=django.db.models.Count('id')
    ).order_by('-count')
    for stat in source_stats:
        print(f"  {stat['source']}: {stat['count']} 条")


def check_api_request() -> None:
    """检查 api_request 表"""
    print_separator("api_request 表详情 (ApiRequest)")
    
    from testmanager_app.models import ApiRequest
    
    requests = ApiRequest.objects.all().order_by('-created_at')[:20]
    
    if not requests:
        print("无数据")
        return
    
    print(f"总数据量: {ApiRequest.objects.count()}")
    print()
    print(f"{'ID':<6} {'方法':<8} {'名称':<30} {'URL':<50} {'创建时间':<20}")
    print("-" * 120)
    
    for r in requests:
        created = r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '-'
        url = (r.url[:48] + '...') if len(r.url) > 50 else r.url
        print(f"{r.id:<6} {r.method:<8} {r.name[:28]:<30} {url:<50} {created:<20}")


def check_ai_saved_data() -> None:
    """检查 AI 保存的数据"""
    print_separator("AI 保存的数据分析")
    
    from testmanager_app.models import FeatureTestCase, TestScript
    
    # 检查 feature_test_case 中 AI 相关的数据
    ai_keywords = ['AI', 'ai', '生成', 'Generated', 'ChatBot', 'chatbot']
    ai_cases = FeatureTestCase.objects.none()
    for keyword in ai_keywords:
        ai_cases = ai_cases | FeatureTestCase.objects.filter(title__icontains=keyword)
    ai_cases = ai_cases.distinct()
    
    print(f"feature_test_case (标题含AI关键词): {ai_cases.count()} 条")
    for tc in ai_cases[:10]:
        created = tc.created_at.strftime('%Y-%m-%d %H:%M') if tc.created_at else '-'
        print(f"  - [{tc.id}] {tc.title[:50]} ({created})")
    
    print()
    
    # 检查 test_script 中 source='chatbot' 的数据
    chatbot_scripts = TestScript.objects.filter(source='chatbot')
    print(f"test_script (source='chatbot'): {chatbot_scripts.count()} 条")
    for s in chatbot_scripts[:10]:
        created = s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '-'
        print(f"  - [{s.id}] {s.name[:50]} ({created})")


def check_data_duplicates() -> None:
    """检查可能的数据重复"""
    print_separator("数据重复检查")
    
    from testmanager_app.models import FeatureTestCase, TestScript
    
    # 检查同一时间创建的记录
    print("同一分钟内创建的 feature_test_case 记录:")
    from django.db.models import Count
    from django.db.models.functions import TruncMinute
    
    minute_groups = (
        FeatureTestCase.objects
        .annotate(created_minute=TruncMinute('created_at'))
        .values('created_minute')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('-created_minute')[:10]
    )
    
    for group in minute_groups:
        print(f"  {group['created_minute']}: {group['count']} 条")
        cases = FeatureTestCase.objects.filter(
            created_at__gte=group['created_minute'],
            created_at__lt=group['created_minute'] + timezone.timedelta(minutes=1)
        )
        for tc in cases:
            print(f"    - [{tc.id}] {tc.title[:50]}")
    
    print()
    
    print("同一分钟内创建的 test_script 记录:")
    minute_groups = (
        TestScript.objects
        .annotate(created_minute=TruncMinute('created_at'))
        .values('created_minute')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .order_by('-created_minute')[:10]
    )
    
    for group in minute_groups:
        print(f"  {group['created_minute']}: {group['count']} 条")
        scripts = TestScript.objects.filter(
            created_at__gte=group['created_minute'],
            created_at__lt=group['created_minute'] + timezone.timedelta(minutes=1)
        )
        for s in scripts:
            print(f"    - [{s.id}] {s.name[:50]}")


def check_model_relationships() -> None:
    """检查模型之间的关系"""
    print_separator("模型关系检查")
    
    from core.models.test_management import TestExecution
    
    # 检查 TestExecution 关联的模型
    print("TestExecution 关联统计:")
    
    total = TestExecution.objects.count()
    with_api_request = TestExecution.objects.filter(api_request__isnull=False).count()
    with_test_script = TestExecution.objects.filter(test_script__isnull=False).count()
    with_collection = TestExecution.objects.filter(collection_execution__isnull=False).count()
    
    print(f"  总执行记录: {total}")
    print(f"  关联 ApiRequest: {with_api_request}")
    print(f"  关联 TestScript: {with_test_script}")
    print(f"  关联 CollectionExecution: {with_collection}")


def main() -> None:
    """主函数"""
    print("\n" + "=" * 80)
    print("  测试用例数据诊断报告")
    print(f"  生成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        check_table_counts()
        check_core_test_case()
        check_feature_test_case()
        check_test_script()
        check_api_request()
        check_ai_saved_data()
        check_data_duplicates()
        check_model_relationships()
        
        print_separator("诊断完成")
        print("\n总结:")
        print("1. core_test_case 已迁移到 FeatureTestCase 模型")
        print("2. feature_test_case - FeatureTestCase 模型，功能测试用例")
        print("3. test_script - TestScript 模型，测试脚本配置")
        print("4. api_request - ApiRequest 模型，API 测试用例")
        print()
        print("建议:")
        print("- 检查 core_test_case 是否有前端页面使用")
        print("- 检查 AI 保存的数据分布在哪些表中")
        print("- 检查 expected_result 为空的记录")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
