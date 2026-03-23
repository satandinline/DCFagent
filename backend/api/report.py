from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["report"])


@router.get("/report/health")
async def report_health():
    """Placeholder – report export functionality coming soon."""
    return {"status": "report module ready", "export_formats": ["pdf", "xlsx"]}
