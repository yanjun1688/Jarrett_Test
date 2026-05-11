#!/usr/bin/env python
"""此脚本依赖的 TestCase 模型已删除，请检查 FeatureTestCase 表"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testmanager.settings')
django.setup()

print('TestCase 模型已删除，功能测试用例已统一迁移到 FeatureTestCase 模型')
print('请查看 feature_test_case 表')

