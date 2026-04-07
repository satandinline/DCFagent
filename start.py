"""
DCF Valuation Agent - 一键启动脚本
同时启动后端服务和前端开发服务器
"""
import subprocess
import time
import sys
import os
import signal
import requests
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 配置
BACKEND_PORT = 5050
FRONTEND_PORT = 3000
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
API_HEALTH_URL = f"{BACKEND_URL}/api/health"

# 全局进程对象
backend_process = None
frontend_process = None


def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("  DCF Valuation Agent - 启动脚本")
    print("=" * 60)
    print()


def print_status(msg, status="INFO"):
    """打印状态信息"""
    statuses = {
        "INFO": "\033[94m[INFO]\033[0m",
        "SUCCESS": "\033[92m[SUCCESS]\033[0m",
        "WARNING": "\033[93m[WARNING]\033[0m",
        "ERROR": "\033[91m[ERROR]\033[0m",
    }
    print(f"{statuses.get(status, '[INFO]')} {msg}")


def check_port_available(port):
    """检查端口是否可用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except OSError:
        return False


def find_executable(name):
    """查找可执行文件路径"""
    import shutil
    path = shutil.which(name)
    if path:
        return path
    # Windows上可能需要添加.cmd后缀
    if sys.platform == 'win32':
        path = shutil.which(name + '.cmd')
        if path:
            return path
        # 尝试npx
        npx_path = shutil.which('npx')
        if npx_path:
            return npx_path
    return name  # 返回原名称，让系统自己找


def wait_for_backend(max_wait=60):
    """等待后端启动成功"""
    print_status(f"等待后端服务启动 (最多等待 {max_wait} 秒)...", "INFO")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(API_HEALTH_URL, timeout=2)
            if response.status_code == 200:
                elapsed = time.time() - start_time
                print_status(f"后端服务启动成功! (耗时 {elapsed:.1f}秒)", "SUCCESS")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # 每2秒尝试一次
        time.sleep(2)
        elapsed = int(time.time() - start_time)
        print_status(f"等待中... ({elapsed}s)", "INFO")
    
    print_status("后端服务启动超时!", "ERROR")
    return False


def start_backend():
    """启动后端服务"""
    global backend_process
    
    # 检查端口
    if not check_port_available(BACKEND_PORT):
        print_status(f"后端端口 {BACKEND_PORT} 已被占用，尝试停止现有进程...", "WARNING")
        kill_process_on_port(BACKEND_PORT)
        time.sleep(1)
    
    print_status("启动后端服务 (FastAPI on port 5050)...", "INFO")
    
    try:
        # 启动后端
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            # Windows-specific
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        # 实时输出后端日志（截取最后几行）
        print_status("后端服务日志:", "INFO")
        
        # 等待后端启动
        if wait_for_backend():
            return True
        else:
            print_status("后端启动失败，查看最近日志:", "ERROR")
            # 这里可以添加查看日志的逻辑
            return False
            
    except Exception as e:
        print_status(f"启动后端失败: {e}", "ERROR")
        return False


def start_frontend():
    """启动前端服务"""
    global frontend_process
    
    # 检查端口
    if not check_port_available(FRONTEND_PORT):
        print_status(f"前端端口 {FRONTEND_PORT} 已被占用，尝试停止现有进程...", "WARNING")
        kill_process_on_port(FRONTEND_PORT)
        time.sleep(1)
    
    print_status("启动前端服务 (Vite on port 3000)...", "INFO")
    
    try:
        # 查找npm路径
        import shutil
        npm_cmd = shutil.which('npm') or 'npm'
        
        # 检查node_modules是否存在
        node_modules = FRONTEND_DIR / "node_modules"
        if not node_modules.exists():
            print_status("node_modules 不存在，正在安装依赖...", "WARNING")
            install_result = subprocess.run(
                [npm_cmd, "install"],
                cwd=str(FRONTEND_DIR),
                capture_output=True,
                text=True
            )
            if install_result.returncode != 0:
                print_status(f"依赖安装失败: {install_result.stderr}", "ERROR")
                return False
            print_status("依赖安装完成!", "SUCCESS")
        
        # 启动前端
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            # Windows-specific
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        )
        
        print_status("前端服务启动中...", "INFO")
        
        # 等待前端启动
        time.sleep(5)
        
        print_status("前端服务已启动!", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"启动前端失败: {e}", "ERROR")
        return False


def kill_process_on_port(port):
    """杀死占用指定端口的进程"""
    try:
        if sys.platform == 'win32':
            # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                    print_status(f"已停止占用端口 {port} 的进程 (PID: {pid})", "INFO")
        else:
            # Unix/Linux/Mac
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True)
            print_status(f"已停止占用端口 {port} 的进程", "INFO")
    except Exception as e:
        print_status(f"停止进程时出错: {e}", "WARNING")


def cleanup():
    """清理进程"""
    print()
    print_status("正在关闭服务...", "INFO")
    
    if backend_process:
        try:
            if sys.platform == 'win32':
                backend_process.terminate()
            else:
                os.killpg(os.getpgid(backend_process.pid), signal.SIGTERM)
            print_status("后端服务已停止", "INFO")
        except:
            pass
    
    if frontend_process:
        try:
            if sys.platform == 'win32':
                frontend_process.terminate()
            else:
                os.killpg(os.getpgid(frontend_process.pid), signal.SIGTERM)
            print_status("前端服务已停止", "INFO")
        except:
            pass


def main():
    """主函数"""
    print_banner()
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print_status("需要 Python 3.8 或更高版本!", "ERROR")
        sys.exit(1)
    
    # 检查必要的目录
    if not BACKEND_DIR.exists():
        print_status(f"后端目录不存在: {BACKEND_DIR}", "ERROR")
        sys.exit(1)
    
    if not FRONTEND_DIR.exists():
        print_status(f"前端目录不存在: {FRONTEND_DIR}", "ERROR")
        sys.exit(1)
    
    # 检查.env文件
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        print_status(f".env 文件不存在，正在创建...", "WARNING")
        env_example = BACKEND_DIR / ".env.example"
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print_status("请编辑 backend/.env 文件配置必要的环境变量", "INFO")
    
    print_status("=" * 60)
    print_status("步骤 1: 启动后端服务")
    print_status("=" * 60)
    
    if not start_backend():
        cleanup()
        sys.exit(1)
    
    print()
    print_status("=" * 60)
    print_status("步骤 2: 启动前端服务")
    print_status("=" * 60)
    
    if not start_frontend():
        cleanup()
        sys.exit(1)
    
    print()
    print_status("=" * 60)
    print_status("启动完成!")
    print_status("=" * 60)
    print()
    print(f"\033[92m后端地址:\033[0m {BACKEND_URL}")
    print(f"\033[92m前端地址:\033[0m {FRONTEND_URL}")
    print()
    print("\033[1m\033[94m请在浏览器中打开前端地址访问应用\033[0m")
    print()
    print("按 Ctrl+C 停止所有服务")
    print()
    
    # 注册清理函数
    import atexit
    atexit.register(cleanup)
    
    # 处理中断信号
    def signal_handler(sig, frame):
        print("\n")
        print_status("收到停止信号，正在关闭...", "WARNING")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 保持运行
    try:
        while True:
            time.sleep(1)
            # 检查进程状态
            if backend_process and backend_process.poll() is not None:
                print_status("后端进程意外退出!", "ERROR")
                break
            if frontend_process and frontend_process.poll() is not None:
                print_status("前端进程意外退出!", "ERROR")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
