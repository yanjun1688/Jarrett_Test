"""
异步操作辅助工具
提供全局复用的事件循环，避免重复创建
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# 全局事件循环实例
_global_event_loop = None


def get_event_loop():
    """
    获取全局复用的事件循环

    避免每次调用都创建新的事件循环，提升性能
    如果现有的事件循环已关闭，会创建新的循环

    Returns:
        asyncio.AbstractEventLoop: 事件循环实例

    使用示例:
        loop = get_event_loop()
        result = loop.run_until_complete(async_function())
    """
    global _global_event_loop

    if _global_event_loop is None:
        try:
            # 尝试获取当前线程的事件循环
            _global_event_loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            _global_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_global_event_loop)
            logger.info("Created new global event loop")
    else:
        # 检查现有的全局事件循环是否已关闭
        if _global_event_loop.is_closed():
            # 创建新的事件循环替换已关闭的循环
            _global_event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_global_event_loop)
            logger.info("Created new global event loop after detecting closed loop")

    return _global_event_loop


def reset_event_loop():
    """
    重置全局事件循环

    在测试或特殊情况下调用，关闭并重新创建事件循环
    """
    global _global_event_loop

    if _global_event_loop is not None:
        try:
            # 尝试关闭已存在的事件循环
            if not _global_event_loop.is_closed():
                _global_event_loop.close()
                logger.info("Closed existing global event loop")
        except Exception as e:
            logger.warning(f"Error closing event loop: {e}")

    # 创建新的事件循环
    _global_event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_global_event_loop)
    logger.info("Created new global event loop after reset")

    return _global_event_loop
