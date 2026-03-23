#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键启动脚本：同时启动前端和后端服务
"""
import sys
from pathlib import Path

# 将项目根目录和 backend 目录添加到 Python 路径
root_dir = Path(__file__).parent
backend_dir = root_dir / 'backend'

sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

# 现在可以安全导入其他模块
import subprocess
import time
import webbrowser
import socket
import requests
import threading

# 提前导入后端应用（确保路径已设置）
from main import app as backend_app
import uvicorn


def check_port_available(port: int, host: str = '127.0.0.1') -> bool:
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def wait_for_backend(port: int = 8001, timeout: int = 30) -> bool:
    """
    等待后端服务启动
    
    Args:
        port: 后端服务端口
        timeout: 超时时间（秒）
    
    Returns:
        bool: 后端是否成功启动
    """
    print(f"⏳ 等待后端服务启动（最多 {timeout} 秒）...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if check_port_available(port):
            # 端口已开放，尝试访问健康检查接口
            try:
                response = requests.get(f'http://localhost:{port}/api/health', timeout=2)
                if response.status_code == 200:
                    print(f"✅ 后端服务已成功启动（响应正常）")
                    return True
            except Exception:
                pass
            # 端口开放但健康检查失败，继续等待
            time.sleep(0.5)
        else:
            time.sleep(0.5)
    
    print(f"❌ 后端服务启动超时（{timeout} 秒）")
    return False


def main():
    # 获取项目根目录（已在文件开头设置）
    backend_dir = root_dir / 'backend'
    frontend_dir = root_dir / 'frontend'
    
    print("=" * 60)
    print("🚀 DCF Valuation Agent - 启动服务")
    print("=" * 60)
    
    # 1. 检查前端依赖
    if not (frontend_dir / 'node_modules').exists():
        print("\n⚠️  检测到前端依赖未安装，正在安装...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
    
    # 2. 启动后端服务器（后台运行）
    print("\n🔧 启动后端服务器...")
    
    # 使用线程启动后端
    def run_backend():
        try:
            uvicorn.run(backend_app, host='0.0.0.0', port=8001, reload=False, log_level='error')
        except Exception as e:
            print(f"❌ 后端启动失败：{e}")
    
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # 3. 等待后端启动并验证
    print("⏳ 等待后端服务启动...")
    time.sleep(3)  # 给后端一些时间初始化
    
    if not wait_for_backend(port=8001, timeout=30):
        print("\n❌ 后端服务启动失败，请检查错误日志")
        return
    
    # 4. 后端启动成功后，启动前端开发服务器
    print("\n📱 启动前端开发服务器...")
    frontend_process = subprocess.Popen(
        ['npm', 'run', 'dev'],
        cwd=frontend_dir,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8'
    )
    
    # 5. 等待前端启动
    print("⏳ 等待前端服务启动...")
    time.sleep(5)
    
    # 6. 打开浏览器访问前端页面
    print("\n🌐 打开浏览器访问 http://localhost:3000")
    webbrowser.open('http://localhost:3000')
    
    try:
        print("=" * 60)
        print("💡 提示：按 Ctrl+C 停止所有服务")
        print("=" * 60)
        
        # 保持运行，等待用户中断
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 正在关闭服务...")
    finally:
        # 关闭前端进程
        if 'frontend_process' in locals():
            frontend_process.terminate()
            frontend_process.wait()
        print("✅ 所有服务已关闭")


if __name__ == '__main__':
    main()
