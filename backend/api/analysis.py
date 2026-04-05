from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.models.schemas import (
    CalculateRequest,
    DCFResult,
    NarrativeRequest,
    NarrativeResponse,
    SensitivityMatrix,
)
from backend.services import dcf_service
from backend.services.llm_service import LLMService

router = APIRouter(tags=["analysis"])


@router.post("/calculate", response_model=DCFResult)
async def calculate_dcf(req: CalculateRequest, save_to_db: bool = Query(default=True)):
    try:
        result = dcf_service.run_dcf(req.financial_data, req.parameters)
        
        # Save to database if requested
        if save_to_db and req.financial_data.ticker:
            try:
                # Generate sensitivity analysis for storage
                sens_matrix = dcf_service.sensitivity_analysis(req.financial_data, req.parameters)
                
                # Generate narrative
                llm = LLMService()
                narrative_text = await llm.generate_narrative(
                    req.financial_data.model_dump(),
                    result.model_dump(),
                )
                
                # Save valuation result
                dcf_service.save_valuation_to_db(
                    financial_data=req.financial_data,
                    params=req.parameters,
                    dcf_result=result,
                    sensitivity_matrix=sens_matrix,
                    narrative=narrative_text,
                    created_by="api_user"
                )
            except Exception as save_err:
                print(f"Warning: Failed to save valuation to database: {save_err}")
        
        return result
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


@router.get("/trends/{ticker}")
async def get_trends(ticker: str):
    """Get trend analysis and valuation history for a ticker"""
    try:
        trends_data = dcf_service.get_trend_analysis(ticker)
        return {
            "success": True,
            "data": trends_data
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/load-from-db/{ticker}")
async def load_from_db(ticker: str):
    """Load financial data from database for a ticker"""
    try:
        financial_data = dcf_service.load_financial_data_from_db(ticker)
        if not financial_data:
            raise HTTPException(status_code=404, detail=f"No data found for ticker: {ticker}")
        
        return {
            "success": True,
            "financial_data": financial_data.model_dump()
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/valuation-history/{ticker}")
async def valuation_history(ticker: str, limit: int = Query(default=10)):
    """Get valuation history for a ticker"""
    try:
        from backend.services.db_service import db_service
        history = db_service.get_valuation_history(ticker, limit=limit)
        
        return {
            "success": True,
            "ticker": ticker,
            "count": len(history),
            "valuations": [
                {
                    "id": h['id'],
                    "date": str(h['valuation_date']),
                    "company_name": h.get('company_name'),
                    "per_share_value": float(h['per_share_value']) if h.get('per_share_value') else None,
                    "enterprise_value": float(h['enterprise_value']) if h.get('enterprise_value') else None,
                    "equity_value": float(h['equity_value']) if h.get('equity_value') else None,
                    "wacc_used": float(h['wacc_used']) if h.get('wacc_used') else None,
                    "current_price": float(h['current_price']) if h.get('current_price') else None,
                    "upside_downside": float(h['upside_downside']) if h.get('upside_downside') else None,
                    "created_by": h.get('created_by')
                }
                for h in history
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
