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

# Agent Configuration
AGENT_ENABLED: bool = os.getenv("AGENT_ENABLED", "false").lower() == "true"
AGENT_INTERVAL_HOURS: int = int(os.getenv("AGENT_INTERVAL_HOURS", "24"))

# Email Configuration
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_HOST: str = os.getenv("QQ_EMAIL_HOST", "smtp.qq.com")
EMAIL_PORT: int = int(os.getenv("QQ_EMAIL_PORT", "587"))
EMAIL_USER: str = os.getenv("QQ_EMAIL_USER", "")
EMAIL_PASSWORD: str = os.getenv("QQ_EMAIL_PASSWORD", "")
EMAIL_TO: str = os.getenv("EMAIL_TO", "")
