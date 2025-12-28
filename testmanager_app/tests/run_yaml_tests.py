#!/usr/bin/env python
"""
YAML配置工具测试运行脚本
一键运行所有YAML相关测试
"""

import subprocess
import sys

def run_tests():
    """运行所有YAML相关测试"""
    commands = [
        ["pytest", "testmanager_app/tests/test_yaml_validator.py", "-v", "--tb=short"],
        ["pytest", "testmanager_app/tests/test_yaml_converter.py", "-v", "--tb=short"],
        ["pytest", "testmanager_app/tests/test_yaml_api.py", "-v", "--tb=short"],
    ]

    overall_success = True

    for cmd in commands:
        print("\n" + "=" * 80)
        print(f"Running: {' '.join(cmd)}")
        print("=" * 80 + "\n")

        result = subprocess.run(cmd)
        if result.returncode != 0:
            overall_success = False

    print("\n" + "=" * 80)
    if overall_success:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请查看上面的输出")
    print("=" * 80)

    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(run_tests())
