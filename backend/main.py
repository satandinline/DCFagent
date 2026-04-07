from __future__ import annotations

import sys
import os
from pathlib import Path

# 将项目根目录添加到 sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import exception handling
from backend.exception_handlers import ExceptionHandlerMiddleware

# 使用 backend 前缀的导入（从项目根目录运行时需要）
try:
    from backend.api import analysis, report, upload, agent
    from backend.api.agent import router as agent_router
    from backend.api.agent_management import router as agent_management_router
    from backend.api.scheduled import router as scheduled_router
    from backend.config import UPLOAD_DIR, AGENT_ENABLED, AGENT_INTERVAL_HOURS
except ModuleNotFoundError:
    # 回退到相对导入（从 backend 目录运行时）
    from api import analysis, report, upload, agent
    from api.agent import router as agent_router
    from api.agent_management import router as agent_management_router
    from api.scheduled import router as scheduled_router
    from config import UPLOAD_DIR, AGENT_ENABLED, AGENT_INTERVAL_HOURS


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize scheduler for LangGraph agent if enabled
    if AGENT_ENABLED:
        try:
            from backend.agent.langgraph_agent import langgraph_agent
            from backend.services.scheduler_service import scheduler_service
        except ModuleNotFoundError:
            from agent.langgraph_agent import langgraph_agent
            from services.scheduler_service import scheduler_service
        
        try:
            scheduler_service.init_scheduler()
            scheduler_service.start()
            langgraph_agent.start_scheduled(interval_hours=AGENT_INTERVAL_HOURS)
            print(f"DCF LangGraph Agent scheduler started: every {AGENT_INTERVAL_HOURS} hours")
        except Exception as e:
            print(f"Warning: Failed to start agent scheduler: {e}")
    
    # Initialize Data Fetch Scheduler (runs at 00:00 and 12:00)
    try:
        try:
            from backend.services.data_fetch_scheduler import data_fetch_scheduler
        except ModuleNotFoundError:
            from services.data_fetch_scheduler import data_fetch_scheduler
        
        data_fetch_scheduler.init_scheduler()
        data_fetch_scheduler.start()
        data_fetch_scheduler.setup_scheduled_jobs()
        print("Data Fetch Scheduler started: 00:00 and 12:00 daily")
    except Exception as e:
        print(f"Warning: Failed to start Data Fetch Scheduler: {e}")
    
    yield
    
    # Cleanup
    if AGENT_ENABLED:
        try:
            from backend.services.scheduler_service import scheduler_service
        except ModuleNotFoundError:
            from services.scheduler_service import scheduler_service
        try:
            scheduler_service.stop()
        except Exception:
            pass
    
    # Stop Data Fetch Scheduler
    try:
        try:
            from backend.services.data_fetch_scheduler import data_fetch_scheduler
        except ModuleNotFoundError:
            from services.data_fetch_scheduler import data_fetch_scheduler
        data_fetch_scheduler.stop()
    except Exception:
        pass


app = FastAPI(
    title="DCF Valuation Agent API (LangGraph)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add global exception handling middleware
app.add_middleware(ExceptionHandlerMiddleware, debug=False)

app.include_router(upload.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(agent_management_router, prefix="/api")
app.include_router(scheduled_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
