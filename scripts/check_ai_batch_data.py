#!/usr/bin/env python
"""检查同一时间创建的数据（AI 批量保存的证据）"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

from django.utils import timezone
from testmanager_app.models import FeatureTestCase, TestScript


def print_separator(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_same_minute_data() -> None:
    """检查同一分钟内创建的数据"""
    print_separator("同一分钟内创建的数据（AI 批量保存的证据）")
    
    # feature_test_case
    print("\n【feature_test_case 表】")
    all_cases = list(FeatureTestCase.objects.all().order_by('created_at'))
    minute_groups = {}
    for tc in all_cases:
        minute_key = tc.created_at.strftime('%Y-%m-%d %H:%M')
        if minute_key not in minute_groups:
            minute_groups[minute_key] = []
        minute_groups[minute_key].append(tc)
    
    for minute, cases in sorted(minute_groups.items(), reverse=True):
        if len(cases) > 1:
            print(f"\n  时间: {minute} ({len(cases)} 条)")
            for tc in cases:
                print(f"    - [{tc.id}] {tc.title[:50]}")
    
    # test_script
    print("\n【test_script 表】")
    all_scripts = list(TestScript.objects.all().order_by('created_at'))
    minute_groups = {}
    for s in all_scripts:
        minute_key = s.created_at.strftime('%Y-%m-%d %H:%M')
        if minute_key not in minute_groups:
            minute_groups[minute_key] = []
        minute_groups[minute_key].append(s)
    
    for minute, scripts in sorted(minute_groups.items(), reverse=True):
        if len(scripts) > 1:
            print(f"\n  时间: {minute} ({len(scripts)} 条)")
            for s in scripts:
                print(f"    - [{s.id}] {s.name[:50]} (source={s.source})")


def check_expected_result_format() -> None:
    """检查 expected_result 字段的格式"""
    print_separator("expected_result 字段格式分析")
    
    print("\n【feature_test_case 表】")
    for tc in FeatureTestCase.objects.all()[:5]:
        print(f"\n  ID: {tc.id}, 标题: {tc.title[:40]}")
        print(f"  expected_result: {tc.expected_result[:100]}")
        print(f"  expected_result 长度: {len(tc.expected_result)}")


def check_test_script_content() -> None:
    """检查 test_script 表中 AI 保存的内容"""
    print_separator("test_script 表中 AI 保存的内容格式")
    
    chatbot_scripts = TestScript.objects.filter(source='chatbot').order_by('-created_at')[:3]
    
    for s in chatbot_scripts:
        print(f"\n  ID: {s.id}, 名称: {s.name}")
        print(f"  类型: {s.script_type}")
        print(f"  来源: {s.source}")
        print(f"  内容前 500 字符:")
        print(f"  {s.content[:500]}")
        print("-" * 60)


def main() -> None:
    print("\n" + "=" * 80)
    print("  AI 保存数据分析报告")
    print(f"  生成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    check_same_minute_data()
    check_expected_result_format()
    check_test_script_content()
    
    print_separator("总结")
    print("""
1. core_test_case 表已删除 (TestCase 模型已废弃)
2. feature_test_case 表有数据 (使用 FeatureTestCase 模型)
   - 需要检查是否有同一时间创建的

3. test_script 表有 7 条 AI 保存的数据（source='chatbot'）
   - 内容是 JSON 格式的 API 测试配置

问题分析：
- 正则 (?:\[预期结果\]|预期结果[：:])\s*(.+) 只匹配第一行
- 现在 AI 生成的 markdown 是表格格式，没有 [预期结果] 模式
- 所以 expected_result 为空，保存失败
""")


if __name__ == '__main__':
    main()
