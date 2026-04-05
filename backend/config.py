import os
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv()

MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL: str = "https://api.minimaxi.com/v1"
MINIMAX_MODEL: str = "MiniMax-M2.7-highspeed"

# MySQL Configuration
MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "dcf_estimation")

UPLOAD_DIR: Path = _backend_dir / "temp_uploads"
