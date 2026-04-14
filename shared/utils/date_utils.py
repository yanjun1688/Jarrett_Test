"""
日期时间工具
提供跨模块使用的日期时间处理功能
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional, Union, List
import pytz


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象
        format_str: 格式字符串
        
    Returns:
        str: 格式化后的字符串
    """
    return dt.strftime(format_str)


def parse_datetime(datetime_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    解析日期时间字符串
    
    Args:
        datetime_str: 日期时间字符串
        format_str: 格式字符串
        
    Returns:
        datetime or None: 解析后的日期时间对象
    """
    try:
        return datetime.strptime(datetime_str, format_str)
    except (ValueError, TypeError):
        return None


def get_time_ago(dt: datetime) -> str:
    """
    获取相对时间描述（如"2小时前"）
    
    Args:
        dt: 日期时间对象
        
    Returns:
        str: 相对时间描述
    """
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years}年前"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months}个月前"
    elif diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"


def convert_timezone(dt: datetime, from_tz: str = "UTC", to_tz: str = "Asia/Shanghai") -> datetime:
    """
    转换时区
    
    Args:
        dt: 日期时间对象
        from_tz: 原始时区
        to_tz: 目标时区
        
    Returns:
        datetime: 转换后的日期时间对象
    """
    try:
        from_zone = pytz.timezone(from_tz)
        to_zone = pytz.timezone(to_tz)
        
        if dt.tzinfo is None:
            dt = from_zone.localize(dt)
        
        return dt.astimezone(to_zone)
    except Exception:
        return dt


def get_date_range(start_date: Union[str, datetime, None], end_date: Union[str, datetime, None]) -> List[date]:
    """
    获取日期范围内的所有日期
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        list: 日期列表
    """
    start_dt = parse_datetime(start_date, "%Y-%m-%d") if isinstance(start_date, str) else start_date
    end_dt = parse_datetime(end_date, "%Y-%m-%d") if isinstance(end_date, str) else end_date
    
    if not start_dt or not end_dt:
        return []
    
    date_list = []
    current_date = start_dt.date()
    end_date_obj = end_dt.date()
    
    while current_date <= end_date_obj:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    
    return date_list
