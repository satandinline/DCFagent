import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量（支持项目根目录和 backend 目录的 .env 文件）
_project_root = Path(__file__).resolve().parent.parent
_backend_dir = Path(__file__).resolve().parent

load_dotenv(_project_root / ".env")
load_dotenv(_backend_dir / ".env")
load_dotenv()

MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL: str = "https://api.minimaxi.com/v1"
MINIMAX_MODEL: str = "MiniMax-M2.7-highspeed"

UPLOAD_DIR: Path = _backend_dir / "temp_uploads"
