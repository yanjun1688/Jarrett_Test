"""
异步工具函数
"""

from __future__ import annotations

import asyncio
import subprocess
import time
import os
import sys
from typing import Any, Callable, Dict, List, Optional, TypeVar, Coroutine, Union
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from ..exceptions import ExecutionError

T = TypeVar('T')


async def run_async(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """在异步上下文中运行同步函数
    
    Args:
        func: 要运行的同步函数
        *args: 函数参数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    loop = asyncio.get_running_loop()
    
    # 如果函数已经是协程，直接运行
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    
    # 否则在线程池中运行
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def batch_process(
    items: List[Any],
    process_func: Callable[[Any], Coroutine[Any, Any, T]],
    batch_size: int = 10,
    max_concurrent: int = 5
) -> List[T]:
    """批量处理项目
    
    Args:
        items: 要处理的项目列表
        process_func: 处理函数（必须是异步函数）
        batch_size: 每批处理的数量
        max_concurrent: 最大并发数
        
    Returns:
        处理结果列表
    """
    results = []
    
    # 分批处理
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # 创建任务
        tasks = []
        for item in batch:
            task = asyncio.create_task(process_func(item))
            tasks.append(task)
        
        # 限制并发
        batch_results = []
        for j in range(0, len(tasks), max_concurrent):
            current_tasks = tasks[j:j + max_concurrent]
            current_results = await asyncio.gather(*current_tasks, return_exceptions=True)
            batch_results.extend(current_results)
        
        # 处理异常
        for result in batch_results:
            if isinstance(result, Exception):
                raise ExecutionError(f"批量处理失败: {str(result)}")
            results.append(result)
    
    return results


def with_timeout(timeout: float) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """为异步函数添加超时控制的装饰器
    
    Args:
        timeout: 超时时间（秒）
        
    Example:
        @with_timeout(5.0)
        async def my_async_function():
            await asyncio.sleep(10)  # 这会超时
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise ExecutionError(f"操作超时: 超过 {timeout} 秒")
        
        return wrapper
    return decorator


async def retry_async(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> T:
    """重试异步函数
    
    Args:
        func: 要重试的异步函数
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exceptions: 触发重试的异常类型
        
    Returns:
        函数执行结果
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_attempts:
                break
            
            # 计算延迟时间
            current_delay = delay * (backoff_factor ** (attempt - 1))
            
            # 记录重试信息
            print(f"尝试 {attempt}/{max_attempts} 失败: {str(e)}，{current_delay:.1f}秒后重试...")
            await asyncio.sleep(current_delay)
    
    raise ExecutionError(f"重试 {max_attempts} 次后仍然失败: {str(last_exception)}")


async def parallel_execute(
    *coroutines: Coroutine[Any, Any, T],
    max_concurrent: Optional[int] = None
) -> List[T]:
    """并行执行多个协程
    
    Args:
        *coroutines: 要执行的协程
        max_concurrent: 最大并发数，如果为None则不限制
        
    Returns:
        执行结果列表
    """
    if max_concurrent is None:
        # 不限制并发
        return await asyncio.gather(*coroutines, return_exceptions=False)
    else:
        # 限制并发
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(coro: Coroutine[Any, Any, T]) -> T:
            async with semaphore:
                return await coro
        
        tasks = [asyncio.create_task(run_with_semaphore(coro)) for coro in coroutines]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results


async def measure_execution_time(coro: Coroutine[Any, Any, T]) -> tuple[T, float]:
    """测量协程执行时间
    
    Args:
        coro: 要测量的协程
        
    Returns:
        (执行结果, 执行时间)
    """
    start_time = time.time()
    result = await coro
    end_time = time.time()
    return result, end_time - start_time


class AsyncQueue:
    """异步队列"""
    
    def __init__(self, maxsize: int = 0):
        self._queue = asyncio.Queue(maxsize=maxsize)
    
    async def put(self, item: Any):
        """放入项目"""
        await self._queue.put(item)
    
    async def get(self) -> Any:
        """获取项目"""
        return await self._queue.get()
    
    def qsize(self) -> int:
        """队列大小"""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()
    
    def full(self) -> bool:
        """队列是否已满"""
        return self._queue.full()
    
    async def process(
        self,
        process_func: Callable[[Any], Coroutine[Any, Any, Any]],
        num_workers: int = 1
    ):
        """处理队列中的项目
        
        Args:
            process_func: 处理函数
            num_workers: 工作线程数
        """
        async def worker():
            while True:
                try:
                    item = await self.get()
                    await process_func(item)
                    self._queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"处理项目失败: {str(e)}")
                    self._queue.task_done()
        
        # 创建工作线程
        workers = [asyncio.create_task(worker()) for _ in range(num_workers)]
        
        # 等待所有项目处理完成
        await self._queue.join()
        
        # 取消工作线程
        for worker_task in workers:
            worker_task.cancel()
        
        # 等待工作线程结束
        await asyncio.gather(*workers, return_exceptions=True)


async def run_in_threadpool(
    func: Callable[..., T],
    *args,
    max_workers: int = 10,
    **kwargs
) -> T:
    """在线程池中运行函数
    
    Args:
        func: 要运行的函数
        *args: 函数参数
        max_workers: 最大工作线程数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    loop = asyncio.get_running_loop()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return await loop.run_in_executor(
            executor,
            lambda: func(*args, **kwargs)
        )


async def run_in_processpool(
    func: Callable[..., T],
    *args,
    max_workers: int = 4,
    **kwargs
) -> T:
    """在进程池中运行函数（适用于CPU密集型任务）
    
    Args:
        func: 要运行的函数
        *args: 函数参数
        max_workers: 最大工作进程数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    loop = asyncio.get_running_loop()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return await loop.run_in_executor(
            executor,
            lambda: func(*args, **kwargs)
        )


async def async_run_command(
    command: Union[str, List[str]],
    timeout: float = 120.0,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False
) -> Dict[str, Any]:
    """
    异步执行命令（跨平台兼容）
    
    使用 asyncio.to_thread + subprocess.run 避免事件循环限制，
    适用于 Windows SelectorEventLoop 环境。
    
    Args:
        command: 命令，可以是字符串或列表
        timeout: 超时时间（秒），默认 120 秒
        cwd: 工作目录
        env: 环境变量字典
        shell: 是否使用 shell 执行
        capture_output: 是否捕获输出
        text: 是否以文本模式返回输出
        check: 是否在非零返回码时抛出异常
        
    Returns:
        dict: {
            "success": bool,  # 命令是否成功（returncode == 0）
            "returncode": int,  # 返回码
            "stdout": str,  # 标准输出
            "stderr": str,  # 标准错误
            "error": Optional[str]  # 错误信息（如果有）
        }
        
    Raises:
        subprocess.TimeoutExpired: 命令执行超时
        FileNotFoundError: 命令未找到
        subprocess.CalledProcessError: check=True 且返回码非零
        
    Example:
        result = await async_run_command(["echo", "hello"])
        if result["success"]:
            print(result["stdout"])
    """
    
    def _run_sync() -> Dict[str, Any]:
        run_env = env if env is not None else None
        
        if isinstance(command, list):
            cmd = command
            use_shell = shell
        else:
            cmd = command
            use_shell = True
        
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            encoding='utf-8' if text else None,
            errors='replace' if text else None,
            timeout=timeout,
            cwd=cwd,
            env=run_env,
            shell=use_shell,
            check=check
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout if result.stdout else "",
            "stderr": result.stderr if result.stderr else "",
            "error": result.stderr if result.returncode != 0 and result.stderr else None
        }
    
    try:
        return await asyncio.to_thread(_run_sync)
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": f"命令执行超时（{timeout}秒）"
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "error": f"命令未找到: {e}"
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "returncode": e.returncode,
            "stdout": e.stdout if e.stdout else "",
            "stderr": e.stderr if e.stderr else "",
            "error": e.stderr if e.stderr else f"命令返回非零状态码: {e.returncode}"
        }