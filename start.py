#!/usr/bin/env python
"""
统一启动脚本 - 用于启动整个项目的前后端服务
支持启动：Django后端、React前端、Celery Worker

优化版本：
- 重构为类结构，移除全局变量
- 修复 Daphne 进程监控问题
- 优化线程退出机制
- 移除冗余函数
"""
import sys
import subprocess
import os
import platform
import argparse
import time
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Union
from subprocess import Popen, CompletedProcess


class ServiceManager:
    """服务管理器 - 统一管理所有服务的启动、监控和关闭"""
    
    BASE_DIR = Path(__file__).resolve().parent
    FRONTEND_DIR = BASE_DIR / "frontend"
    
    # 常见的虚拟环境目录名
    VENV_DIRS = ["venv", ".venv", "env", ".env"]
    
    def __init__(self) -> None:
        self.python_exe: str = sys.executable
        self.venv_info: Optional[Dict[str, Any]] = None
        self.processes: List[Tuple[str, Popen[str]]] = []
        self.log_threads: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self._daphne_available: Optional[bool] = None
        self._playwright_checked: bool = False
    
    def _find_venv(self) -> Optional[Dict[str, Any]]:
        """查找并缓存虚拟环境目录"""
        if self.venv_info is not None:
            return self.venv_info
        
        for venv_dir in self.VENV_DIRS:
            venv_path = self.BASE_DIR / venv_dir
            if not venv_path.exists():
                continue
            
            if platform.system() == "Windows":
                python_exe = venv_path / "Scripts" / "python.exe"
                scripts_dir = venv_path / "Scripts"
            else:
                python_exe = venv_path / "bin" / "python"
                scripts_dir = venv_path / "bin"
            
            if python_exe.exists():
                self.venv_info = {
                    "path": venv_path,
                    "python": str(python_exe),
                    "scripts_dir": str(scripts_dir)
                }
                return self.venv_info
        
        return None
    
    def _setup_venv(self) -> None:
        """设置虚拟环境"""
        venv_path_env = os.environ.get("VIRTUAL_ENV")
        if venv_path_env:
            print(f"[VENV] 已激活虚拟环境: {venv_path_env}")
            if platform.system() == "Windows":
                python_exe = Path(venv_path_env) / "Scripts" / "python.exe"
            else:
                python_exe = Path(venv_path_env) / "bin" / "python"
            if python_exe.exists():
                self.python_exe = str(python_exe)
            return
        
        venv_info = self._find_venv()
        if venv_info:
            venv_path = venv_info["path"]
            python_exe = venv_info["python"]
            scripts_dir = venv_info["scripts_dir"]
            
            os.environ["VIRTUAL_ENV"] = str(venv_path)
            
            if "PYTHONHOME" in os.environ:
                del os.environ["PYTHONHOME"]
                print("[VENV] 已移除PYTHONHOME环境变量")
            
            current_path = os.environ.get("PATH", "")
            path_sep = ';' if platform.system() == "Windows" else ':'
            path_parts = current_path.split(path_sep)
            filtered_path = [p for p in path_parts if 'Python' not in p or str(venv_path) in p]
            os.environ["PATH"] = f"{scripts_dir}{path_sep}{path_sep.join(filtered_path)}"
            
            self.python_exe = python_exe
            os.environ["PYTHON_EXE"] = python_exe
            
            if platform.system() == "Windows":
                site_packages = Path(venv_path) / "Lib" / "site-packages"
            else:
                site_packages = None
                for minor in range(20, 5, -1):
                    candidate = Path(venv_path) / "lib" / f"python3.{minor}" / "site-packages"
                    if candidate.exists():
                        site_packages = candidate
                        break
                if not site_packages:
                    site_packages = Path(venv_path) / "lib" / "python" / "site-packages"
            
            if site_packages and site_packages.exists():
                os.environ["PYTHONPATH"] = str(site_packages)
                print(f"[VENV] 设置PYTHONPATH: {site_packages}")
            
            print(f"[VENV] [OK] 已激活虚拟环境: {venv_path}")
            print(f"[VENV] Python: {python_exe}")
        else:
            print("[WARN] 未检测到虚拟环境")
            print("[WARN] 建议创建虚拟环境: python -m venv venv")
            self.python_exe = sys.executable
            os.environ["PYTHON_EXE"] = sys.executable
    
    def _run_cmd(self, cmd: Union[str, List[str]], cwd: Optional[Path] = None, check: bool = True, shell: bool = False, capture: bool = False, timeout: Optional[int] = None) -> CompletedProcess[str]:
        """执行命令的统一方法"""
        if isinstance(cmd, list) and len(cmd) > 0:
            if cmd[0] == sys.executable or cmd[0].endswith("python") or cmd[0].endswith("python.exe"):
                if self.python_exe:
                    cmd = [self.python_exe] + cmd[1:]
            elif cmd[0] == "manage.py" or (len(cmd) > 1 and "manage.py" in cmd):
                if self.python_exe and not cmd[0].endswith("python") and not cmd[0].endswith("python.exe"):
                    cmd = [self.python_exe] + cmd
        
        print(f"[RUN] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        
        env = os.environ.copy()
        if self.python_exe:
            env["PYTHON_EXE"] = self.python_exe
        
        if capture:
            result = subprocess.run(
                cmd, cwd=cwd, shell=shell, env=env,
                capture_output=True, text=True, timeout=timeout, check=False
            )
            return result
        else:
            result = subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env, text=True)
            return result
    
    def _read_stream(self, stream: Any, prefix: str) -> None:
        """实时读取并打印流输出"""
        try:
            for line in iter(stream.readline, ''):
                if self.shutdown_event.is_set():
                    break
                if line:
                    print(f"[{prefix}] {line.rstrip()}")
        except Exception as e:
            if not self.shutdown_event.is_set():
                print(f"[{prefix}] 读取错误: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass
    
    def _start_process_with_logging(self, cmd: List[str], cwd: Path, name: str) -> Popen[str]:
        """启动进程并实时读取日志"""
        env = os.environ.copy()
        if self.python_exe:
            env["PYTHON_EXE"] = self.python_exe
        
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, universal_newlines=True
        )
        
        stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(proc.stdout, name),
            daemon=True, name=f"{name}_stdout"
        )
        stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(proc.stderr, f"{name}_ERROR"),
            daemon=True, name=f"{name}_stderr"
        )
        
        stdout_thread.start()
        stderr_thread.start()
        self.log_threads.extend([stdout_thread, stderr_thread])
        
        return proc
    
    def _should_check_timestamp(self, filepath: Path, days: int = 7) -> bool:
        """检查是否应该执行定期检查"""
        if not filepath.exists():
            return True
        import time
        last_check = filepath.stat().st_mtime
        return (time.time() - last_check) > (days * 24 * 3600)
    
    def _update_timestamp(self, filepath: Path) -> None:
        """更新检查时间戳"""
        filepath.touch()
    
    def _ensure_pip(self) -> None:
        """确保pip是最新版本并安装依赖（快速检查模式）"""
        requirements_file = self.BASE_DIR / "requirements.txt"
        if not requirements_file.exists():
            print(f"[WARN] requirements.txt 不存在: {requirements_file}")
            return
        
        pip_check_file = self.BASE_DIR / ".pip_check_timestamp"
        should_check_pip = self._should_check_timestamp(pip_check_file, days=7)
        
        if should_check_pip:
            print("[ENV] 检查pip更新...")
            try:
                result = self._run_cmd(
                    [self.python_exe, "-m", "pip", "list", "--outdated", "--format=json"],
                    capture=True, timeout=30
                )
                import json
                stdout_str = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='ignore')
                outdated = json.loads(stdout_str) if stdout_str.strip() else []
                pip_outdated = any(p.get("name", "").lower() == "pip" for p in outdated)
                if pip_outdated:
                    print("[ENV] 升级pip...")
                    self._run_cmd([self.python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=False)
                    print("[ENV] [OK] pip升级完成")
                else:
                    print("[ENV] [OK] pip已是最新版本")
                self._update_timestamp(pip_check_file)
            except Exception as e:
                print(f"[WARN] 检查pip更新失败: {e}")
        
        print("[ENV] 检查依赖安装状态...")
        try:
            result = self._run_cmd(
                [self.python_exe, "-m", "pip", "check"],
                capture=True, timeout=30
            )
            if result.returncode == 0:
                print("[ENV] [OK] 依赖已完整安装")
                return
        except Exception:
            pass
        
        print("[ENV] 检测到依赖问题，正在安装requirements.txt...")
        try:
            self._run_cmd([self.python_exe, "-m", "pip", "install", "-r", str(requirements_file)], check=False)
            print("[ENV] [OK] requirements.txt依赖安装完成")
        except Exception as e:
            print(f"[WARN] 安装requirements.txt依赖失败: {e}")
    
    def _check_daphne(self) -> bool:
        """检查并缓存Daphne可用性"""
        if self._daphne_available is not None:
            return self._daphne_available
        
        try:
            result = self._run_cmd(
                [self.python_exe, "-c", "import daphne; print('OK')"],
                capture=True, timeout=5
            )
            stdout_str = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'OK' in stdout_str:
                self._daphne_available = True
                return True
        except Exception:
            pass
        
        self._daphne_available = False
        return False
    
    def _ensure_daphne(self) -> bool:
        """确保daphne已安装"""
        print("[ENV] 检查daphne...")
        
        if self._check_daphne():
            print("[ENV] [OK] daphne已安装")
            return True
        
        print("[ENV] daphne未安装，正在安装...")
        try:
            result = self._run_cmd(
                [self.python_exe, "-m", "pip", "install", "daphne"],
                capture=True, timeout=60
            )
            if result.returncode == 0:
                self._daphne_available = True
                print("[ENV] [OK] daphne安装完成")
                return True
        except Exception as e:
            print(f"[WARN] daphne安装失败: {e}")
        
        print("[WARN] WebSocket功能可能不可用，将使用runserver")
        return False
    
    def _ensure_playwright(self) -> None:
        """确保playwright及其浏览器已安装"""
        if self._playwright_checked:
            return
        
        print("[ENV] 检查playwright...")
        
        try:
            result = self._run_cmd(
                [self.python_exe, "-c", 
                 "import playwright; from playwright._impl._driver import compute_driver_executable; print('OK')"],
                capture=True, timeout=5
            )
            stdout_str = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'OK' in stdout_str:
                print("[ENV] playwright已安装")
            else:
                print("[ENV] playwright导入失败，准备重新安装")
                self._install_playwright()
        except Exception as e:
            print(f"[ENV] 检查playwright时出错: {e}")
            self._install_playwright()
        
        self._ensure_playwright_browser()
        self._playwright_checked = True
    
    def _install_playwright(self) -> None:
        """安装playwright"""
        print("[ENV] 安装playwright...")
        try:
            self._run_cmd([self.python_exe, "-m", "pip", "uninstall", "playwright", "-y"], check=False)
            self._run_cmd([self.python_exe, "-m", "pip", "install", "playwright"], check=False)
            print("[ENV] playwright安装完成")
        except Exception as e:
            print(f"[WARN] 安装playwright失败: {e}")
    
    def _ensure_playwright_browser(self) -> None:
        """确保playwright浏览器已安装"""
        print("[ENV] 检查playwright浏览器...")
        
        try:
            result = self._run_cmd(
                [self.python_exe, "-c",
                 "from playwright.sync_api import sync_playwright; "
                 "p = sync_playwright().start(); "
                 "try: "
                 "  executable_path = p.chromium.executable_path; "
                 "  import os; "
                 "  print('OK' if os.path.exists(executable_path) else 'NOT_FOUND'); "
                 "finally: p.stop()"],
                capture=True, timeout=15
            )
            
            stdout_str = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'OK' in stdout_str:
                print("[ENV] [OK] playwright浏览器已安装")
                return
        except subprocess.TimeoutExpired:
            print("[ENV] 检查playwright浏览器超时，将尝试安装")
        except Exception as e:
            print(f"[ENV] 检查playwright浏览器时出错: {str(e)[:100]}")
        
        print("[ENV] 正在安装playwright浏览器...")
        try:
            self._run_cmd([self.python_exe, "-m", "playwright", "install", "chromium"], check=False)
            print("[ENV] [OK] playwright浏览器安装完成")
        except Exception as e:
            print(f"[WARN] playwright浏览器安装失败: {e}")
    
    def _ensure_node_modules(self) -> None:
        """确保前端node_modules已安装"""
        print("[ENV] 检查前端依赖...")
        node_modules = self.FRONTEND_DIR / "node_modules"
        package_json = self.FRONTEND_DIR / "package.json"
        
        if not package_json.exists():
            print("[WARN] frontend/package.json 不存在，跳过前端依赖检查")
            return
        
        if not node_modules.exists() or not list(node_modules.iterdir()):
            print("[ENV] 安装前端依赖...")
            npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
            self._run_cmd([npm_cmd, "install"], cwd=self.FRONTEND_DIR)
        else:
            print("[ENV] 前端依赖已安装")
    
    def setup_environment(self) -> None:
        """设置所有环境"""
        self._print_header("环境检查与准备")
        
        self._setup_venv()
        
        print(f"[ENV] Python: {self.python_exe}")
        print(f"[ENV] 虚拟环境: {os.environ.get('VIRTUAL_ENV', '未激活')}")
        print(f"[ENV] 工作目录: {self.BASE_DIR}")
        print(f"[ENV] 平台: {platform.system()} {platform.release()}")
        
        self._ensure_pip()
        self._ensure_daphne()
        self._ensure_playwright()
        self._ensure_node_modules()
        
        print("\n[ENV] 环境准备完成!\n")
    
    def start_django(self) -> Optional[Popen[str]]:
        """启动Django后端服务"""
        self._print_header("启动Django后端服务")
        
        if self._check_daphne():
            cmd = [self.python_exe, "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "-t", "600", "--application-close-timeout", "600", "testmanager.asgi:application"]
            print("[INFO] 使用Daphne ASGI服务器 (支持WebSocket, HTTP超时600秒, 应用关闭超时600秒)")
        else:
            cmd = [self.python_exe, "manage.py", "runserver", "0.0.0.0:8000"]
            print("[INFO] 使用Django runserver (不支持WebSocket)")
        
        print(f"[RUN] {' '.join(cmd)}")
        
        proc = self._start_process_with_logging(cmd, self.BASE_DIR, "Django")
        
        time.sleep(2)
        if proc.poll() is not None:
            print(f"[ERROR] Django服务启动失败，返回码: {proc.returncode}")
            return None
        
        return proc
    
    def start_frontend(self) -> Optional[Popen[str]]:
        """启动React前端服务"""
        self._print_header("启动React前端服务")
        
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        cmd = [npm_cmd, "start"]
        
        proc = self._start_process_with_logging(cmd, self.FRONTEND_DIR, "Frontend")
        
        time.sleep(3)
        return proc
    
    def _validate_playwright_for_celery(self) -> None:
        """在启动Celery前验证Playwright环境"""
        print("[CELERY] 验证Playwright环境...")
        
        try:
            result = self._run_cmd([self.python_exe, "--version"], capture=True, timeout=5)
            print(f"[CELERY] [OK] Python解释器可用: {result.stdout.strip()}")
        except Exception as e:
            raise RuntimeError(f"Python解释器不可用 ({self.python_exe}): {e}")
        
        try:
            result = self._run_cmd(
                [self.python_exe, "-c", 
                 "import playwright; from playwright._impl._driver import compute_driver_executable; print('OK')"],
                capture=True, timeout=5
            )
            stdout_str = result.stdout if isinstance(result.stdout, str) else result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'OK' in stdout_str:
                print("[CELERY] [OK] Playwright模块已安装")
            else:
                raise RuntimeError(
                    f"Playwright模块导入失败\n"
                    f"请运行: {self.python_exe} -m pip install playwright && {self.python_exe} -m playwright install chromium"
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Playwright模块导入超时")
        
        try:
            result = self._run_cmd(
                [self.python_exe, "-c",
                 "from playwright.sync_api import sync_playwright; "
                 "p = sync_playwright().start(); "
                 "browser = p.chromium.launch(headless=True); "
                 "browser.close(); p.stop()"],
                capture=True, timeout=15
            )
            if result.returncode == 0:
                print("[CELERY] [OK] Playwright浏览器可正常启动")
            else:
                raise RuntimeError(f"Playwright浏览器无法启动: {result.stderr[:200] if result.stderr else '未知错误'}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Playwright浏览器启动超时")
        
        print("[CELERY] [OK] Playwright环境验证通过")
    
    def start_celery(self, purge: bool = True) -> Optional[Popen[str]]:
        """启动Celery Worker"""
        self._print_header("启动Celery Worker")
        
        self._validate_playwright_for_celery()
        
        # 清空 broker 中积压的任务，避免启动后执行残留任务
        if purge:
            print("[CELERY] 清空积压任务...")
            purge_cmd = [self.python_exe, "-m", "celery", "-A", "testmanager", "purge", "-f"]
            try:
                result = self._run_cmd(purge_cmd, capture=True, timeout=10)
                stdout = result.stdout.strip() if result.stdout else ""
                if result.returncode == 0:
                    print(f"[CELERY] [OK] 积压任务已清空 {stdout}")
                else:
                    print(f"[CELERY] [WARN] purge 返回非零: {result.stderr.strip() if result.stderr else ''}")
            except Exception as e:
                print(f"[CELERY] [WARN] 清空积压任务失败（可忽略）: {e}")
        else:
            print("[CELERY] 跳过清空积压任务（--no-purge）")
        
        cmd = [self.python_exe, "-m", "celery", "-A", "testmanager", "worker", "-l", "info", "-P", "solo"]
        
        env = os.environ.copy()
        env["PYTHON_EXE"] = self.python_exe
        
        venv_info = self._find_venv()
        if venv_info:
            scripts_dir = venv_info["scripts_dir"]
            current_path = env.get("PATH", "")
            if scripts_dir not in current_path:
                path_sep = ';' if platform.system() == "Windows" else ':'
                env["PATH"] = f"{scripts_dir}{path_sep}{current_path}"
        
        print(f"[CELERY] 使用Python: {self.python_exe}")
        print(f"[CELERY] 命令: {' '.join(cmd)}")
        
        proc = self._start_process_with_logging(cmd, self.BASE_DIR, "Celery")
        
        time.sleep(2)
        if proc.poll() is not None:
            print(f"[ERROR] Celery服务启动失败，返回码: {proc.returncode}")
            return None
        
        return proc
    
    def _print_header(self, text: str) -> None:
        """打印带格式的标题"""
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print(f"{'=' * 60}\n")
    
    def _get_child_processes(self, parent_pid: int) -> List[int]:
        """获取子进程PID列表（用于Daphne进程监控）"""
        try:
            import psutil
            parent = psutil.Process(parent_pid)
            return [p.pid for p in parent.children(recursive=True)]
        except ImportError:
            return []
        except psutil.NoSuchProcess:
            return []
    
    def _is_process_alive(self, proc: Popen[str], name: str) -> bool:
        """检查进程是否仍在运行（处理Daphne master-worker模型）"""
        if proc.poll() is not None:
            # Daphne在Windows上可能fork后主进程退出
            # 检查是否有子进程仍在运行
            if "Django" in name or "Daphne" in name.lower():
                try:
                    import psutil
                    # 查找可能的daphne或python进程
                    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            cmdline = p.info.get('cmdline') or []
                            if any('daphne' in str(c).lower() or 'runserver' in str(c) for c in cmdline):
                                if p.info['pid'] != proc.pid:
                                    return True
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except ImportError:
                    pass
            return False
        return True
    
    def monitor(self) -> None:
        """监控所有进程"""
        self._print_header("服务运行中")
        print(f"[INFO] 已启动 {len(self.processes)} 个服务:")
        for name, proc in self.processes:
            print(f"  - {name}: PID {proc.pid}")
        
        print("\n[INFO] 按 Ctrl+C 停止所有服务\n")
        
        try:
            while True:
                time.sleep(1)
                
                for name, proc in self.processes[:]:
                    if not self._is_process_alive(proc, name):
                        print(f"[WARN] {name} 进程已退出 (PID: {proc.pid}, returncode: {proc.returncode})")
                        self.processes.remove((name, proc))
                
                if not self.processes:
                    print("[WARN] 所有服务已停止")
                    break
        except KeyboardInterrupt:
            print("\n\n[INFO] 收到停止信号，正在关闭所有服务...")
    
    def shutdown(self) -> None:
        """关闭所有服务"""
        self.shutdown_event.set()
        
        for name, proc in self.processes:
            try:
                print(f"[INFO] 停止 {name} (PID: {proc.pid})...")
                if platform.system() == "Windows":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"[WARN] {name} 未响应，强制终止...")
                proc.kill()
                proc.wait()
            except Exception as e:
                print(f"[ERROR] 停止 {name} 失败: {e}")
        
        for thread in self.log_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        print("[INFO] 所有服务已停止")


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="统一启动脚本 - 启动项目的前后端服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py                    # 启动所有服务
  python start.py --backend          # 只启动后端
  python start.py --frontend         # 只启动前端
  python start.py --celery           # 只启动Celery
  python start.py --backend --celery # 启动后端和Celery
  python start.py --env-only         # 只检查环境，不启动服务
        """
    )
    
    parser.add_argument("--env-only", action="store_true", help="只检查环境，不启动任何服务")
    parser.add_argument("--backend", action="store_true", help="启动Django后端服务 (默认: 8000)")
    parser.add_argument("--frontend", action="store_true", help="启动React前端服务 (默认: 3000)")
    parser.add_argument("--celery", action="store_true", help="启动Celery Worker")
    parser.add_argument("--no-purge", action="store_true", help="启动Celery时不清空积压任务")
    parser.add_argument("--skip-env", action="store_true", help="跳过环境检查")
    
    args = parser.parse_args()
    
    if not args.env_only and not any([args.backend, args.frontend, args.celery]):
        args.backend = True
        args.frontend = True
        args.celery = True
    
    manager = ServiceManager()
    
    if not args.skip_env:
        manager.setup_environment()
    
    if args.env_only:
        print("[INFO] 环境检查完成，退出")
        return
    
    try:
        if args.backend:
            proc = manager.start_django()
            if proc:
                manager.processes.append(("Django后端", proc))
                time.sleep(2)
        
        if args.frontend:
            proc = manager.start_frontend()
            if proc:
                manager.processes.append(("React前端", proc))
                time.sleep(2)
        
        if args.celery:
            proc = manager.start_celery(purge=not args.no_purge)
            if proc:
                manager.processes.append(("Celery Worker", proc))
                time.sleep(2)
        
        manager.monitor()
    finally:
        manager.shutdown()


if __name__ == "__main__":
    main()