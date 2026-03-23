from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.schemas import (
    CalculateRequest,
    DCFResult,
    NarrativeRequest,
    NarrativeResponse,
    SensitivityMatrix,
)
from services import dcf_service
from services.llm_service import LLMService

router = APIRouter(tags=["analysis"])


@router.post("/calculate", response_model=DCFResult)
async def calculate_dcf(req: CalculateRequest):
    try:
        return dcf_service.run_dcf(req.financial_data, req.parameters)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sensitivity", response_model=SensitivityMatrix)
async def sensitivity(req: CalculateRequest):
    try:
        return dcf_service.sensitivity_analysis(req.financial_data, req.parameters)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/narrative", response_model=NarrativeResponse)
async def narrative(req: NarrativeRequest):
    try:
        llm = LLMService()
        text = await llm.generate_narrative(
            req.financial_data.model_dump(),
            req.dcf_result.model_dump(),
        )
        return NarrativeResponse(success=True, narrative=text)
    except Exception as exc:
        return NarrativeResponse(success=False, error=str(exc))
