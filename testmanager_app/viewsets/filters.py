"""
通用过滤工具函数
提供安全的参数获取和验证功能
"""

import re


def safe_get_int_param(request_or_params, param_name):
    """
    安全获取整数查询参数

    先从query_params获取参数值，然后尝试转换为整数。
    如果转换失败或参数不存在，返回None。

    参数:
        request_or_params: 请求对象或query_params字典
        param_name: 参数名称

    返回:
        int or None: 转换后的整数值或None

    示例:
        project_id = safe_get_int_param(request, 'project')
        if project_id is not None:
            queryset = queryset.filter(project=project_id)
    """
    # 支持传入request对象或直接传入query_params
    if hasattr(request_or_params, 'query_params'):
        query_params = request_or_params.query_params
    else:
        query_params = request_or_params

    value = query_params.get(param_name, None)
    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_get_str_param(request_or_params, param_name):
    """
    安全获取字符串查询参数并进行简单验证

    从query_params获取参数值，使用正则表达式验证字符串格式。
    只允许字母、数字、空格、下划线、连字符、点和中文字符。
    阻止SQL注入和XSS攻击。

    参数:
        request_or_params: 请求对象或query_params字典
        param_name: 参数名称

    返回:
        str or None: 验证通过的字符串或None

    示例:
        name = safe_get_str_param(request, 'name')
        if name is not None:
            queryset = queryset.filter(name__icontains=name)
    """
    # 支持传入request对象或直接传入query_params
    if hasattr(request_or_params, 'query_params'):
        query_params = request_or_params.query_params
    else:
        query_params = request_or_params

    value = query_params.get(param_name, None)
    if value is None:
        return None

    # 只允许字母、数字、空格、下划线、连字符、点和中文字符
    # 阻止SQL注入和XSS攻击
    # 最大长度200个字符
    if re.match(r'^[a-zA-Z0-9\s\-_.\u4e00-\u9fa5]{0,200}$', str(value)):
        return value
    return None


def safe_get_choice_param(request_or_params, param_name, choices):
    """
    安全获取选项查询参数

    从query_params获取参数值，并验证是否在允许的选项列表中。

    参数:
        request_or_params: 请求对象或query_params字典
        param_name: 参数名称
        choices: 允许的值列表或元组

    返回:
        str or None: 验证通过的选项值或None

    示例:
        status = safe_get_choice_param(request, 'status', ['pending', 'passed', 'failed'])
        if status is not None:
            queryset = queryset.filter(status=status)
    """
    # 支持传入request对象或直接传入query_params
    if hasattr(request_or_params, 'query_params'):
        query_params = request_or_params.query_params
    else:
        query_params = request_or_params

    value = query_params.get(param_name, None)
    if value is None or value not in choices:
        return None
    return value
