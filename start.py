#!/usr/bin/env python
"""
统一启动脚本 - 用于启动整个项目的前后端服务
支持启动：Django后端、React前端、Celery Worker

修复重点：确保 Celery worker 使用正确的 venv Python 解释器
"""
import sys
import subprocess
import os
import platform
import argparse
import time
import signal
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"


def find_venv():
    """查找虚拟环境目录"""
    # 常见的虚拟环境目录名
    venv_dirs = ["venv", ".venv", "env", ".env"]
    
    for venv_dir in venv_dirs:
        venv_path = BASE_DIR / venv_dir
        if not venv_path.exists():
            continue
            
        if platform.system() == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
            scripts_dir = venv_path / "Scripts"
        else:
            python_exe = venv_path / "bin" / "python"
            scripts_dir = venv_path / "bin"
        
        if python_exe.exists():
            return {
                "path": venv_path,
                "python": str(python_exe),
                "scripts_dir": str(scripts_dir)
            }
    
    return None


def activate_venv():
    """激活虚拟环境(设置环境变量)"""
    global PYTHON_EXE
    
    # 如果当前已经在虚拟环境中，直接返回
    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        print(f"[VENV] 已激活虚拟环境: {venv_path}")
        if platform.system() == "Windows":
            python_exe = Path(venv_path) / "Scripts" / "python.exe"
        else:
            python_exe = Path(venv_path) / "bin" / "python"
        if python_exe.exists():
            PYTHON_EXE = str(python_exe)
        return
    
    # 查找虚拟环境
    venv_info = find_venv()
    if venv_info:
        venv_path = venv_info["path"]
        python_exe = venv_info["python"]
        scripts_dir = venv_info["scripts_dir"]
        
        # 设置虚拟环境相关的环境变量
        os.environ["VIRTUAL_ENV"] = str(venv_path)
        
        # 【关键修复】移除 PYTHONHOME，避免冲突
        if "PYTHONHOME" in os.environ:
            del os.environ["PYTHONHOME"]
            print("[VENV] 已移除PYTHONHOME环境变量")
        
        # 更新PATH，将虚拟环境的Scripts/bin目录放在最前面
        current_path = os.environ.get("PATH", "")
        # 移除其他Python路径，确保venv优先
        path_parts = current_path.split(';' if platform.system() == "Windows" else ':')
        # 过滤掉其他Python路径
        filtered_path = [p for p in path_parts if 'Python' not in p or str(venv_path) in p]
        # 将venv的Scripts放在最前面
        if platform.system() == "Windows":
            os.environ["PATH"] = f"{scripts_dir};{';'.join(filtered_path)}"
        else:
            os.environ["PATH"] = f"{scripts_dir}:{':'.join(filtered_path)}"
        
        # 设置PYTHON_EXE
        PYTHON_EXE = python_exe
        # 设置环境变量，使子进程和Celery worker可以访问
        os.environ["PYTHON_EXE"] = python_exe
        
        # 【新增】明确设置PYTHONPATH指向venv的site-packages
        if platform.system() == "Windows":
            site_packages = Path(venv_path) / "Lib" / "site-packages"
        else:
            # Linux/Mac的site-packages路径可能不同，需要查找
            site_packages_candidates = [
                Path(venv_path) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
                Path(venv_path) / "lib" / "python" / "site-packages",
            ]
            site_packages = None
            for candidate in site_packages_candidates:
                if candidate.exists():
                    site_packages = candidate
                    break
        
        if site_packages and site_packages.exists():
            os.environ["PYTHONPATH"] = str(site_packages)
        print(f"[VENV] 设置PYTHONPATH: {site_packages}")
        
        print(f"[VENV] [OK] 已激活虚拟环境: {venv_path}")
        print(f"[VENV] Python: {python_exe}")
    else:
        print("[WARN] ⚠ 未检测到虚拟环境")
        print("[WARN] 建议创建虚拟环境: python -m venv venv")
        print("[WARN] 继续使用系统Python(可能导致依赖安装到全局环境)")
        PYTHON_EXE = sys.executable
        # 设置环境变量，使子进程和Celery worker可以访问
        os.environ["PYTHON_EXE"] = sys.executable


def print_header(text):
    """打印带格式的标题"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


# 全局变量：存储Python解释器路径
PYTHON_EXE = None


def run(cmd, cwd=None, check=True, shell=False, background=False):
    """执行命令"""
    # 如果命令以python或manage.py开头，使用虚拟环境的Python
    if isinstance(cmd, list) and len(cmd) > 0:
        if cmd[0] == sys.executable or cmd[0].endswith("python") or cmd[0].endswith("python.exe"):
            # 替换为虚拟环境的Python
            if PYTHON_EXE:
                cmd = [PYTHON_EXE] + cmd[1:]
        elif cmd[0] == "manage.py" or (len(cmd) > 1 and "manage.py" in cmd):
            # manage.py命令，确保使用正确的Python
            if PYTHON_EXE:
                # 如果第一个参数不是Python，在开头插入Python
                if not cmd[0].endswith("python") and not cmd[0].endswith("python.exe"):
                    cmd = [PYTHON_EXE] + cmd
    
    print(f"[RUN] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    # 准备环境变量(包含激活的虚拟环境信息)
    env = os.environ.copy()
    
    # Windows上设置环境变量以确保Playwright正常工作
    if platform.system() == "Windows":
        # 设置PYTHONASYNCIODEBUG环境变量
        env["PYTHONASYNCIODEBUG"] = "1"
    
    # 确保PYTHON_EXE环境变量传递给子进程
    if PYTHON_EXE:
        env["PYTHON_EXE"] = PYTHON_EXE
    
    if background:
        # 后台运行，需要实时读取输出
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=shell,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # 行缓冲
            universal_newlines=True
        )
        return proc
    else:
        # 前台运行
        result = subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env)
        return result


def read_stream(stream, prefix):
    """实时读取并打印流输出"""
    try:
        for line in iter(stream.readline, ''):
            if line:
                print(f"[{prefix}] {line.rstrip()}")
    except Exception as e:
        print(f"[{prefix}] 读取错误: {e}")
    finally:
        try:
            stream.close()
        except:
            pass


def start_process_with_logging(cmd, cwd, env, name):
    """启动进程并实时读取日志"""
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 启动线程实时读取输出
    import threading
    stdout_thread = threading.Thread(
        target=read_stream,
        args=(proc.stdout, name),
        daemon=True,
        name=f"{name}_stdout"
    )
    stderr_thread = threading.Thread(
        target=read_stream,
        args=(proc.stderr, f"{name}_ERROR"),
        daemon=True,
        name=f"{name}_stderr"
    )
    
    stdout_thread.start()
    stderr_thread.start()
    
    return proc


def ensure_pip():
    """确保pip是最新版本，并安装所有requirements.txt中的依赖"""
    print("[ENV] 升级pip...")
    try:
        python_exe = PYTHON_EXE or sys.executable
        run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=False)
        print("[ENV] [OK] pip升级完成")
    except Exception as e:
        print(f"[WARN] 升级pip失败: {e}")
    
    # 安装requirements.txt中的所有依赖
    print("[ENV] 安装requirements.txt中的依赖...")
    requirements_file = BASE_DIR / "requirements.txt"
    if requirements_file.exists():
        try:
            python_exe = PYTHON_EXE or sys.executable
            print(f"[ENV] 从 {requirements_file} 安装依赖...")
            run([
                python_exe, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=False)
            print("[ENV] [OK] requirements.txt依赖安装完成")
        except Exception as e:
            print(f"[WARN] 安装requirements.txt依赖失败: {e}")
    else:
        print(f"[WARN] requirements.txt 不存在: {requirements_file}")


def ensure_dependencies():
    """确保Python依赖已安装（已迁移到ensure_pip中，此方法保留用于兼容）"""
    # 依赖安装已迁移到ensure_pip方法中，避免重复安装
    print("[ENV] 依赖安装已在ensure_pip中完成，跳过")


def ensure_playwright():
    """确保playwright已安装"""
    print("[ENV] 检查playwright...")
    python_exe = PYTHON_EXE or sys.executable
    
    # 先检查当前是否已安装（修复：不使用__version__）
    try:
        result = subprocess.run(
            [python_exe, "-c", 
             "import playwright; "
             "from playwright._impl._driver import compute_driver_executable; "
             "print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False  # 不抛异常
        )
        
        if result.returncode == 0 and 'OK' in result.stdout:
            print(f"[ENV] playwright已安装")
            return
        else:
            # 导入失败，显示错误并重新安装
            print(f"[ENV] playwright导入失败，准备重新安装")
            print(f"[ENV] 错误信息: {result.stderr}")
    except Exception as e:
        print(f"[ENV] 检查playwright时出错: {e}")
    
    # 重新安装playwright
    print("[ENV] 安装playwright...")
    try:
        # 先卸载
        subprocess.run(
            [python_exe, "-m", "pip", "uninstall", "playwright", "-y"],
            capture_output=True,
            timeout=30
        )
        # 再安装
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "playwright"],
            capture_output=True,
            text=True,
            timeout=120,
            check=True
        )
        print(f"[ENV] playwright安装完成")
    except Exception as e:
        print(f"[WARN] 安装playwright失败: {e}")


def ensure_playwright_browser():
    """确保playwright浏览器已安装"""
    print("[ENV] 检查playwright浏览器...")
    python_exe = PYTHON_EXE or sys.executable
    
    try:
        # 首先尝试使用Playwright的API检查浏览器是否已安装（更快更可靠）
        # 而不是尝试启动浏览器（可能因为其他原因失败）
        result = subprocess.run(
            [python_exe, "-c", 
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); "
             "try: "
             "  # 检查chromium是否已安装（不启动浏览器）"
             "  executable_path = p.chromium.executable_path; "
             "  import os; "
             "  if os.path.exists(executable_path): "
             "    print('OK'); "
             "  else: "
             "    raise Exception('Browser not installed'); "
             "finally: "
             "  p.stop()"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        
        if result.returncode == 0 and 'OK' in result.stdout:
            print("[ENV] [OK] playwright浏览器已安装")
            return
        
        # 如果检查失败，尝试启动浏览器验证（备用方法）
        print("[ENV] 通过API检查未确认，尝试启动浏览器验证...")
        result = subprocess.run(
            [python_exe, "-c",
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); "
             "browser = p.chromium.launch(headless=True); "
             "browser.close(); p.stop()"],
            capture_output=True,
            text=True,
            timeout=60,  # Windows 上 Playwright 启动可能较慢，增加超时时间
            check=False
        )
        
        if result.returncode == 0:
            print("[ENV] [OK] playwright浏览器已安装（通过启动验证）")
            return
            
    except subprocess.TimeoutExpired:
        print("[ENV] 检查playwright浏览器超时，将尝试安装")
    except Exception as e:
        print(f"[ENV] 检查playwright浏览器时出错: {str(e)[:100]}")
    
    # 如果检查失败，尝试安装
    print("[ENV] playwright浏览器未安装或不可用，正在安装...")
    try:
        run([python_exe, "-m", "playwright", "install", "chromium"], check=False)
        print("[ENV] [OK] playwright浏览器安装完成")
    except Exception as e:
        print(f"[WARN] playwright浏览器安装失败: {e}")
        print("[WARN] 录制功能可能不可用")


def ensure_node_modules():
    """确保前端node_modules已安装"""
    print("[ENV] 检查前端依赖...")
    node_modules = FRONTEND_DIR / "node_modules"
    package_json = FRONTEND_DIR / "package.json"
    
    if not package_json.exists():
        print("[WARN] frontend/package.json 不存在，跳过前端依赖检查")
        return
    
    if not node_modules.exists() or not list(node_modules.iterdir()):
        print("[ENV] 安装前端依赖...")
        if platform.system() == "Windows":
            npm_cmd = "npm.cmd"
        else:
            npm_cmd = "npm"
        run([npm_cmd, "install"], cwd=FRONTEND_DIR)
    else:
        print("[ENV] 前端依赖已安装")


def ensure_daphne():
    """确保daphne已安装（用于ASGI服务器和WebSocket支持）"""
    print("[ENV] 检查daphne...")
    python_exe = PYTHON_EXE or sys.executable
    
    try:
        result = subprocess.run(
            [python_exe, "-c", "import daphne; print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        
        if result.returncode == 0 and 'OK' in result.stdout:
            print("[ENV] [OK] daphne已安装")
            return True
        else:
            print("[ENV] daphne未安装，正在安装...")
            print(f"[ENV] 错误信息: {result.stderr}")
            # 尝试安装
            try:
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "daphne"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=True
                )
                print("[ENV] [OK] daphne安装完成")
                return True
            except Exception as e:
                print(f"[WARN] daphne安装失败: {e}")
                print("[WARN] WebSocket功能可能不可用，将使用runserver")
                return False
    except Exception as e:
        print(f"[WARN] 检查daphne时出错: {e}")
        return False


def ensure_env():
    """确保环境准备就绪"""
    global PYTHON_EXE
    
    print_header("环境检查与准备")
    
    # 激活虚拟环境(设置环境变量)
    activate_venv()
    
    print(f"[ENV] Python: {PYTHON_EXE}")
    print(f"[ENV] 虚拟环境: {os.environ.get('VIRTUAL_ENV', '未激活')}")
    print(f"[ENV] 工作目录: {BASE_DIR}")
    print(f"[ENV] 平台: {platform.system()} {platform.release()}")
    
    ensure_pip()
    ensure_dependencies()
    ensure_daphne()  # 添加daphne检查
    ensure_playwright()
    ensure_playwright_browser()
    ensure_node_modules()
    
    print("\n[ENV] 环境准备完成!\n")


def start_django():
    """启动Django后端服务（优先使用Daphne ASGI服务器以支持WebSocket，否则使用runserver）"""
    print_header("启动Django后端服务")
    python_exe = PYTHON_EXE or sys.executable
    
    # Windows上设置环境变量以确保Playwright正常工作
    env = os.environ.copy()
    if platform.system() == "Windows":
        # 设置环境变量以确保使用正确的事件循环策略
        env["PYTHONASYNCIODEBUG"] = "1"
    
    # 检查daphne是否可用
    use_daphne = False
    try:
        # 先尝试导入检查（更快更可靠）
        import_check = subprocess.run(
            [python_exe, "-c", "import daphne; print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        
        if import_check.returncode == 0 and 'OK' in import_check.stdout:
            # 导入成功，再尝试运行命令检查
            result = subprocess.run(
                [python_exe, "-m", "daphne", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            
            # 如果命令执行成功，或者导入成功（即使命令失败也可能是因为参数问题）
            if result.returncode == 0 or import_check.returncode == 0:
                use_daphne = True
                version_info = result.stdout.strip() if result.returncode == 0 else "已安装"
                print(f"[INFO] [OK] 检测到Daphne ({version_info})，使用ASGI服务器 (支持WebSocket)")
            else:
                print(f"[WARN] Daphne导入成功但命令执行失败，将使用runserver")
                print(f"[WARN] 错误信息: {result.stderr}")
        else:
            print(f"[WARN] Daphne不可用（未安装或导入失败），将使用runserver (不支持WebSocket)")
            print(f"[WARN] 错误信息: {import_check.stderr}")
            print(f"[WARN] 建议安装: {python_exe} -m pip install daphne")
    except Exception as e:
        print(f"[WARN] 检查Daphne失败: {e}，将使用runserver")
    
    if use_daphne:
        # Windows上确保事件循环策略在 Daphne 启动前设置
        if platform.system() == "Windows":
            # Windows上使用默认的ProactorEventLoopPolicy
            # Playwright需要Proactor才能创建子进程
            cmd = [python_exe, "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "testmanager.asgi:application"]
            print("[INFO] Windows环境变量: PYTHONASYNCIODEBUG=1")
            print("[INFO] 使用默认 WindowsProactorEventLoopPolicy (Playwright需要)")
        else:
            cmd = [python_exe, "-m", "daphne", "-b", "0.0.0.0", "-p", "8000", "testmanager.asgi:application"]
    else:
        cmd = [python_exe, "manage.py", "runserver", "0.0.0.0:8000"]
        print("[INFO] 使用Django runserver (不支持WebSocket，录制功能可能受限)")
    
    print(f"[RUN] {' '.join(cmd)}")
    
    # 使用新的日志输出功能
    proc = start_process_with_logging(cmd, BASE_DIR, env, "Django")
    
    # 短暂等待以检测启动错误
    time.sleep(2)
    if proc.poll() is not None:
        raise RuntimeError(f"Django服务启动失败，返回码: {proc.returncode}")
    
    return proc


def start_frontend():
    """启动React前端服务"""
    print_header("启动React前端服务")
    if platform.system() == "Windows":
        npm_cmd = "npm.cmd"
    else:
        npm_cmd = "npm"
    cmd = [npm_cmd, "start"]
    env = os.environ.copy()
    
    # 使用新的日志输出功能
    proc = start_process_with_logging(cmd, FRONTEND_DIR, env, "Frontend")
    
    # 前端启动需要更长时间，稍作等待
    time.sleep(3)
    
    return proc


def diagnose_python_environment(python_exe):
    """诊断Python环境，查找问题根源"""
    print(f"\n[DIAGNOSE] 开始诊断Python环境: {python_exe}")
    
    # 1. 检查Python可执行文件是否存在
    print(f"[DIAGNOSE] 检查Python可执行文件...")
    if not Path(python_exe).exists():
        print(f"[ERROR] Python可执行文件不存在: {python_exe}")
        return
    print(f"[DIAGNOSE] [OK] Python可执行文件存在")
    
    # 2. 检查sys.path
    print(f"[DIAGNOSE] 检查sys.path...")
    try:
        result = subprocess.run(
            [python_exe, "-c", "import sys; print('\\n'.join(sys.path))"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        print(f"[DIAGNOSE] sys.path内容:")
        for line in result.stdout.strip().split('\n'):
            if line:
                print(f"  - {line}")
    except Exception as e:
        print(f"[ERROR] 无法获取sys.path: {e}")
    
    # 3. 检查site-packages中是否有playwright
    print(f"[DIAGNOSE] 检查playwright包位置...")
    try:
        result = subprocess.run(
            [python_exe, "-c", 
             "import sys, os; "
             "site_packages = [p for p in sys.path if 'site-packages' in p]; "
             "print('\\n'.join(site_packages))"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        site_packages_dirs = result.stdout.strip().split('\n')
        for sp_dir in site_packages_dirs:
            if sp_dir and Path(sp_dir).exists():
                playwright_dir = Path(sp_dir) / "playwright"
                if playwright_dir.exists():
                    print(f"[DIAGNOSE] [OK] 找到playwright包: {playwright_dir}")
                else:
                    print(f"[DIAGNOSE] ✗ site-packages中无playwright: {sp_dir}")
    except Exception as e:
        print(f"[ERROR] 检查site-packages失败: {e}")
    
    # 4. 尝试导入playwright并捕获详细错误
    print(f"[DIAGNOSE] 尝试导入playwright...")
    try:
        # 修复：playwright的版本信息在 playwright.__version__ 或 playwright._repo_version
        result = subprocess.run(
            [python_exe, "-c", 
             "import playwright; "
             "from playwright._impl._driver import compute_driver_executable; "
             "print('playwright导入成功')"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False  # 不抛异常，手动检查
        )
        if result.returncode == 0:
            print(f"[DIAGNOSE] [OK] {result.stdout.strip()}")
        else:
            print(f"[ERROR] playwright导入失败!")
            print(f"[ERROR] 返回码: {result.returncode}")
            print(f"[ERROR] stdout: {result.stdout}")
            print(f"[ERROR] stderr: {result.stderr}")
    except Exception as e:
        print(f"[ERROR] 执行导入测试失败: {e}")
    
    print(f"[DIAGNOSE] 诊断完成\n")


def validate_playwright_for_celery():
    """
    在启动Celery前强制校验Playwright(Python + 浏览器)
    确保Celery worker使用的Python解释器与安装playwright的venv一致
    
    Raises:
        RuntimeError: 如果验证失败
    """
    python_exe = PYTHON_EXE or sys.executable
    
    if not python_exe:
        raise RuntimeError("PYTHON_EXE 未设置，无法验证Playwright环境")
    
    print("[CELERY] 验证Playwright环境...")
    
    # 1. 验证Python解释器可执行性
    try:
        result = subprocess.run(
            [python_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        print(f"[CELERY] [OK] Python解释器可用: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"Python解释器不可用 ({python_exe}): {str(e)}")
    
    # 2. 验证playwright模块可导入（增强错误诊断）
    try:
        # 修复：不使用__version__，只测试导入
        result = subprocess.run(
            [python_exe, "-c", 
             "import playwright; "
             "from playwright._impl._driver import compute_driver_executable; "
             "print('OK')"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False  # 不立即抛异常，先获取详细信息
        )
        
        if result.returncode == 0 and 'OK' in result.stdout:
            print(f"[CELERY] [OK] Playwright模块已安装并可用")
        else:
            # 导入失败，运行诊断
            print(f"[ERROR] Playwright模块导入失败!")
            print(f"[ERROR] 返回码: {result.returncode}")
            print(f"[ERROR] stdout: {result.stdout}")
            print(f"[ERROR] stderr: {result.stderr}")
            
            # 运行详细诊断
            diagnose_python_environment(python_exe)
            
            raise RuntimeError(
                f"Playwright模块导入失败 ({python_exe})\n"
                f"错误信息: {result.stderr}\n"
                f"请检查上方诊断信息，可能需要重新安装playwright:\n"
                f"{python_exe} -m pip uninstall playwright -y\n"
                f"{python_exe} -m pip install playwright\n"
                f"{python_exe} -m playwright install chromium"
            )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Playwright模块导入超时 ({python_exe})")
    
    # 3. 验证浏览器可启动
    try:
        result = subprocess.run(
            [python_exe, "-c",
             "from playwright.sync_api import sync_playwright; "
             "p = sync_playwright().start(); "
             "browser = p.chromium.launch(headless=True); "
             "browser.close(); p.stop()"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True
        )
        print("[CELERY] [OK] Playwright浏览器可正常启动")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        error_str = str(error_msg) if error_msg else "未知错误"
        raise RuntimeError(
            f"Playwright浏览器无法启动 ({python_exe}): {error_str[:200]}\n"
            f"请运行: {python_exe} -m playwright install chromium"
        )
    
    print("[CELERY] [OK] Playwright环境验证通过")


def start_celery():
    """
    启动Celery Worker
    
    关键修复：直接使用 venv 的 Python 可执行文件启动 Celery，
    而不是通过当前 Python 的 -m celery 方式启动。
    这样确保 Celery worker 运行时使用的就是 venv 的 Python 环境。
    """
    print_header("启动Celery Worker")
    
    # 强制校验Playwright环境
    validate_playwright_for_celery()
    
    python_exe = PYTHON_EXE or sys.executable
    
    # 【核心修复】：直接用 venv 的 Python 启动 celery 模块
    # 这样 Celery worker 进程内部导入模块时，使用的就是这个 Python 环境
    cmd = [
        python_exe,  # 使用 venv 的 Python (不是 sys.executable)
        "-m",
        "celery",
        "-A",
        "testmanager",
        "worker",
        "-l",
        "info",
        "-P",
        "solo"  # Windows 下必须使用 solo 池
    ]
    
    # 准备环境变量
    env = os.environ.copy()
    env["PYTHON_EXE"] = python_exe  # 传递给子进程
    
    # 确保 PATH 包含 venv 的 Scripts/bin 目录
    venv_info = find_venv()
    if venv_info:
        scripts_dir = venv_info["scripts_dir"]
        current_path = env.get("PATH", "")
        if scripts_dir not in current_path:
            if platform.system() == "Windows":
                env["PATH"] = f"{scripts_dir};{current_path}"
            else:
                env["PATH"] = f"{scripts_dir}:{current_path}"
    
    print(f"[CELERY] 使用Python: {python_exe}")
    print(f"[CELERY] 命令: {' '.join(cmd)}")
    
    # 使用新的日志输出功能
    proc = start_process_with_logging(cmd, BASE_DIR, env, "Celery")
    
    # 短暂等待以检测启动错误
    time.sleep(2)
    if proc.poll() is not None:
        raise RuntimeError(f"Celery服务启动失败，返回码: {proc.returncode}")
    
    return proc


def main():
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
    
    parser.add_argument(
        "--env-only",
        action="store_true",
        help="只检查环境，不启动任何服务"
    )
    parser.add_argument(
        "--backend",
        action="store_true",
        help="启动Django后端服务 (默认: 8000)"
    )
    parser.add_argument(
        "--frontend",
        action="store_true",
        help="启动React前端服务 (默认: 3000)"
    )
    parser.add_argument(
        "--celery",
        action="store_true",
        help="启动Celery Worker"
    )
    parser.add_argument(
        "--skip-env",
        action="store_true",
        help="跳过环境检查"
    )
    
    args = parser.parse_args()
    
    # 如果没有指定任何服务，默认启动所有
    if not args.env_only and not any([args.backend, args.frontend, args.celery]):
        args.backend = True
        args.frontend = True
        args.celery = True
    
    # 环境检查
    if not args.skip_env:
        ensure_env()
    
    if args.env_only:
        print("[INFO] 环境检查完成，退出")
        return
    
    # 存储进程列表
    processes = []
    
    try:
        # 启动服务
        if args.backend:
            proc = start_django()
            if proc:
                processes.append(("Django后端", proc))
                time.sleep(2)  # 等待服务启动
        
        if args.frontend:
            proc = start_frontend()
            if proc:
                processes.append(("React前端", proc))
                time.sleep(2)
        
        if args.celery:
            proc = start_celery()
            if proc:
                processes.append(("Celery Worker", proc))
                time.sleep(2)
        
        # 打印运行信息
        print_header("服务运行中")
        print(f"[INFO] 已启动 {len(processes)} 个服务:")
        for name, proc in processes:
            print(f"  - {name}: PID {proc.pid}")
        
        print("\n[INFO] 按 Ctrl+C 停止所有服务\n")
        
        # 等待进程
        try:
            while True:
                time.sleep(1)
                # 检查进程是否还在运行
                for name, proc in processes[:]:
                    if proc.poll() is not None:
                        print(f"[WARN] {name} 进程已退出 (PID: {proc.pid}, returncode: {proc.returncode})")
                        processes.remove((name, proc))
                
                if not processes:
                    print("[WARN] 所有服务已停止")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n[INFO] 收到停止信号，正在关闭所有服务...")
            
    finally:
        # 清理进程
        for name, proc in processes:
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
        
        print("[INFO] 所有服务已停止")


if __name__ == "__main__":
    main()