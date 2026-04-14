"""
集合执行输出格式化工具

提供集合执行结果的格式化输出，支持清晰的请求分离和详细信息展示
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Dict, Any


def format_collection_execution_output(results: List[Dict[str, Any]], execution_mode: str) -> str:
    """
    格式化集合执行输出

    Args:
        results: 执行结果列表
        execution_mode: 执行模式（concurrent、sequential、chain）

    Returns:
        str: 格式化的输出字符串
    """
    if not results:
        return "没有执行结果"

    output_parts = []

    # 添加头部信息
    output_parts.append("=" * 80)
    output_parts.append(f"集合执行结果 - 模式: {execution_mode}")
    output_parts.append(f"总请求数: {len(results)}")
    output_parts.append(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_parts.append("=" * 80)
    output_parts.append("")

    # 统计信息
    passed_count = sum(1 for res in results if res.get('success'))
    failed_count = len(results) - passed_count

    output_parts.append(f"📊 统计信息:")
    output_parts.append(f"   ✅ 成功: {passed_count}")
    output_parts.append(f"   ❌ 失败: {failed_count}")
    output_parts.append(f"   📈 通过率: {(passed_count/len(results)*100):.1f}%")
    output_parts.append("")

    # 每个请求的详细信息
    for idx, result in enumerate(results):
        output_parts.append(f"{'='*60}")
        output_parts.append(f"请求 #{idx + 1}")
        output_parts.append(f"{'='*60}")

        # 基本信息
        output_parts.append(f"📝 基本信息:")
        output_parts.append(f"   请求ID: {result.get('api_request_id', 'N/A')}")
        output_parts.append(f"   方法: {result.get('request_method', 'N/A')}")
        output_parts.append(f"   URL: {result.get('request_url', 'N/A')}")

        if execution_mode == 'concurrent':
            output_parts.append(f"   执行序号: {result.get('execution_index', 0) + 1}/{result.get('request_count', 1)}")

        # 执行结果
        success = result.get('success', False)
        status_icon = "✅" if success else "❌"
        output_parts.append(f"\n{status_icon} 执行结果:")

        if result.get('error_message'):
            output_parts.append(f"   错误: {result['error_message']}")
        else:
            output_parts.append(f"   HTTP状态码: {result.get('response_status', 'N/A')}")
            output_parts.append(f"   响应时间: {result.get('response_time', 'N/A')} 秒")

            # 响应体摘要
            response_body = result.get('response_body', '')
            if response_body:
                if len(response_body) > 200:
                    output_parts.append(f"   响应体: {response_body[:200]}...")
                else:
                    output_parts.append(f"   响应体: {response_body}")

        # 断言结果
        assertions = result.get('assertions', [])
        if assertions:
            output_parts.append(f"\n🔍 断言验证:")
            for assertion in assertions:
                assertion_status = "✅" if assertion.get('passed') else "❌"
                output_parts.append(f"   {assertion_status} {assertion.get('type', 'unknown')}: {assertion.get('target_value', '')}")

            passed_assertions = sum(1 for a in assertions if a.get('passed'))
            total_assertions = len(assertions)
            output_parts.append(f"   总计: {passed_assertions}/{total_assertions} 通过")

        output_parts.append("")

    # 添加尾部信息
    output_parts.append("=" * 80)
    output_parts.append(f"执行完成 - 总计: {passed_count} 成功, {failed_count} 失败")
    output_parts.append("=" * 80)

    return "\n".join(output_parts)


def format_request_summary(result: Dict[str, Any]) -> str:
    """
    格式化单个请求摘要信息

    Args:
        result: 单个请求的执行结果

    Returns:
        str: 格式化的摘要字符串
    """
    success = result.get('success', False)
    method = result.get('request_method', 'N/A')
    url = result.get('request_url', 'N/A')
    status = result.get('response_status', 'N/A')
    response_time = result.get('response_time', 'N/A')

    status_icon = "✅" if success else "❌"

    if result.get('error_message'):
        return f"{status_icon} {method} {url} - 错误: {result['error_message']}"
    else:
        return f"{status_icon} {method} {url} - 状态: {status} - 耗时: {response_time}s"