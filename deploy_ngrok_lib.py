#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
公网部署脚本：使用 Python ngrok 库启动后端和 ngrok 隧道
不需要单独的 ngrok.exe，直接使用 Python 库

使用方法：
    python deploy_ngrok_lib.py
    
功能：
    1. 自动检查并安装 ngrok 库
    2. 启动后端 FastAPI 服务（端口 8001）
    3. 从 backend/.env 读取 ngrok 认证令牌
    4. 创建 ngrok 隧道
    5. 显示公网访问地址
    6. 自动打开浏览器查看 API 文档
"""
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径（必须在其他 import 之前）
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

import subprocess
import time
import webbrowser
import threading


def main():
    print("=" * 60)
    print("🚀 DCF Valuation Agent - 后端公网部署（Python ngrok 库）")
    print("=" * 60)
    
    # 1. 检查是否安装了 ngrok 库
    try:
        import ngrok
        print("\n✅ ngrok 库已安装")
    except ImportError:
        print("\n❌ 错误：未安装 ngrok 库")
        print("   正在安装...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'ngrok==1.0.0'], check=True)
        import ngrok
    
    # 2. 启动后端服务器（后台运行）
    print("\n🔧 启动后端服务器...")
    from backend.main import app
    import uvicorn
    
    def run_backend():
        uvicorn.run(app, host='0.0.0.0', port=8001, reload=False, log_level='info')
    
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # 等待后端启动
    print("⏳ 等待后端服务启动...")
    time.sleep(3)
    
    # 3. 启动 ngrok 隧道
    print("\n🌐 启动 ngrok 隧道...")
    
    # 从 .env 文件读取配置
    import os
    from dotenv import load_dotenv
    
    env_path = root_dir / 'backend' / '.env'
    load_dotenv(env_path)
    
    ngrok_auth_token = os.getenv('NGROK_AUTH_TOKEN', '')
    
    if not ngrok_auth_token:
        print("\n⚠️  警告：未在 backend/.env 中找到 NGROK_AUTH_TOKEN")
        print("   请确保已正确配置 ngrok 认证令牌")
        return
    
    # 提取实际的 token（去掉前面的命令部分）
    if 'ngrok config add-authtoken' in ngrok_auth_token:
        ngrok_auth_token = ngrok_auth_token.replace('ngrok config add-authtoken', '').strip()
    
    try:
        # 使用 ngrok 库创建隧道
        from ngrok import connect
        
        print(f"\n📡 使用认证令牌连接 ngrok...")
        
        # 创建隧道，连接到本地 8001 端口
        tunnel = connect(
            addr='localhost:8001',
            authtoken=ngrok_auth_token,
            # 如果有指定域名，可以使用以下参数
            # hostname='dcf-estimate-agent.ngrok.io',
        )
        
        # 获取公网 URL
        public_url = tunnel.url()
        
        print("\n" + "=" * 60)
        print("✅ 部署完成！")
        print("=" * 60)
        
        print(f"\n🌍 **后端 API 公网地址**: {public_url}")
        print(f"\n💡 使用说明：")
        print(f"   1. 本地访问前端：http://localhost:3000")
        print(f"   2. 本地访问 API：http://localhost:8001")
        print(f"   3. 公网访问 API：{public_url}")
        print(f"   4. API 文档：{public_url}/docs")
        print(f"\n📝 注意：")
        print(f"   - 前端需要修改 API 请求地址为：{public_url}")
        print(f"   - 或者在 frontend/vite.config.ts 中配置代理")
        
        # 打开浏览器
        print("\n🌐 正在打开 API 文档...")
        webbrowser.open(f'{public_url}/docs')
        
        # 保持运行
        print("\n" + "=" * 60)
        print("💡 按 Ctrl+C 停止所有服务")
        print("=" * 60)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 正在关闭服务...")
            tunnel.close()
            print("✅ 所有服务已关闭")
            
    except Exception as e:
        print(f"\n❌ ngrok 连接失败：{e}")
        print("\n可能的原因：")
        print("   1. 网络连接问题")
        print("   2. ngrok 认证令牌无效")
        print("   3. ngrok 账户限制")
        print("\n请检查 backend/.env 中的 NGROK_AUTH_TOKEN 配置")


if __name__ == '__main__':
    main()
