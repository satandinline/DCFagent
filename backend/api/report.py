from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import io

router = APIRouter(tags=["report"])


@router.get("/report/health")
async def report_health():
    """检查报告模块状态"""
    return {"status": "report module ready", "export_formats": ["pdf", "xlsx", "json"]}


@router.get("/report/{valuation_id}")
async def get_report(valuation_id: int):
    """
    获取指定估值的完整报告
    """
    from backend.services.db_service import db_service
    
    try:
        valuation = db_service.get_valuation_by_id(valuation_id)
        if not valuation:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        return {
            "success": True,
            "report": {
                "company_name": valuation.get('company_name'),
                "ticker": valuation.get('ticker'),
                "fiscal_year": valuation.get('fiscal_year'),
                "valuation_date": str(valuation.get('valuation_date')),
                "currency": valuation.get('currency', 'CNY'),
                "dcf_result": {
                    "per_share_value": float(valuation.get('per_share_value', 0)) if valuation.get('per_share_value') else None,
                    "enterprise_value": float(valuation.get('enterprise_value', 0)) if valuation.get('enterprise_value') else None,
                    "equity_value": float(valuation.get('equity_value', 0)) if valuation.get('equity_value') else None,
                    "wacc_used": float(valuation.get('wacc_used', 0)) if valuation.get('wacc_used') else None,
                    "terminal_growth_rate": float(valuation.get('terminal_growth_rate', 0)) if valuation.get('terminal_growth_rate') else None,
                    "upside_downside": float(valuation.get('upside_downside', 0)) if valuation.get('upside_downside') else None,
                },
                "parameters": {
                    "revenue_growth_rate": float(valuation.get('revenue_growth_rate', 0)) if valuation.get('revenue_growth_rate') else None,
                    "operating_margin": float(valuation.get('operating_margin', 0)) if valuation.get('operating_margin') else None,
                    "tax_rate": float(valuation.get('tax_rate', 0)) if valuation.get('tax_rate') else None,
                    "projection_years": valuation.get('projection_years'),
                },
                "sensitivity_data": json.loads(valuation.get('sensitivity_data', '{}')) if valuation.get('sensitivity_data') else None,
                "narrative": valuation.get('narrative'),
                "created_by": valuation.get('created_by'),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{valuation_id}/download")
async def download_report(valuation_id: int, format: str = "json"):
    """
    下载估值的完整报告
    支持格式: json, txt
    """
    from backend.services.db_service import db_service
    
    try:
        valuation = db_service.get_valuation_by_id(valuation_id)
        if not valuation:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        ticker = valuation.get('ticker', 'unknown')
        filename_prefix = f"dcf_report_{ticker}_{valuation_id}"
        
        if format == "json":
            # 返回JSON格式
            report_data = {
                "DCF Valuation Report": {
                    "Company": valuation.get('company_name'),
                    "Ticker": valuation.get('ticker'),
                    "Fiscal Year": valuation.get('fiscal_year'),
                    "Valuation Date": str(valuation.get('valuation_date')),
                    "Currency": valuation.get('currency', 'CNY'),
                },
                "Valuation Results": {
                    "Per Share Value": float(valuation.get('per_share_value', 0)) if valuation.get('per_share_value') else None,
                    "Enterprise Value": float(valuation.get('enterprise_value', 0)) if valuation.get('enterprise_value') else None,
                    "Equity Value": float(valuation.get('equity_value', 0)) if valuation.get('equity_value') else None,
                    "WACC": float(valuation.get('wacc_used', 0)) if valuation.get('wacc_used') else None,
                    "Terminal Growth Rate": float(valuation.get('terminal_growth_rate', 0)) if valuation.get('terminal_growth_rate') else None,
                    "Upside/Downside": float(valuation.get('upside_downside', 0)) if valuation.get('upside_downside') else None,
                },
                "Parameters Used": {
                    "Revenue Growth Rate": float(valuation.get('revenue_growth_rate', 0)) if valuation.get('revenue_growth_rate') else None,
                    "Operating Margin": float(valuation.get('operating_margin', 0)) if valuation.get('operating_margin') else None,
                    "Tax Rate": float(valuation.get('tax_rate', 0)) if valuation.get('tax_rate') else None,
                    "Projection Years": valuation.get('projection_years'),
                },
                "Analysis Narrative": valuation.get('narrative') or "N/A",
                "Created By": valuation.get('created_by') or "N/A",
            }
            
            content = json.dumps(report_data, indent=2, ensure_ascii=False)
            filename = f"{filename_prefix}.json"
            
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type='application/json',
                headers={'Content-Disposition': f"attachment; filename*=UTF-8''{filename}"}
            )
        
        elif format == "txt":
            # 返回文本格式
            def pct(v):
                return f"{(float(v) * 100 if v else 0):.2f}%"
            
            lines = [
                "=" * 60,
                "DCF VALUATION REPORT",
                "=" * 60,
                "",
                f"Company: {valuation.get('company_name', 'N/A')}",
                f"Ticker: {valuation.get('ticker', 'N/A')}",
                f"Fiscal Year: {valuation.get('fiscal_year', 'N/A')}",
                f"Valuation Date: {valuation.get('valuation_date', 'N/A')}",
                f"Currency: {valuation.get('currency', 'CNY')}",
                "",
                "-" * 40,
                "VALUATION RESULTS",
                "-" * 40,
                f"Per Share Value: {valuation.get('per_share_value', 'N/A')}",
                f"Enterprise Value: {valuation.get('enterprise_value', 'N/A')}",
                f"Equity Value: {valuation.get('equity_value', 'N/A')}",
                f"WACC: {pct(valuation.get('wacc_used'))}",
                f"Terminal Growth Rate: {pct(valuation.get('terminal_growth_rate'))}",
                f"Upside/Downside: {pct(valuation.get('upside_downside'))}",
                "",
                "-" * 40,
                "PARAMETERS USED",
                "-" * 40,
                f"Revenue Growth Rate: {pct(valuation.get('revenue_growth_rate'))}",
                f"Operating Margin: {pct(valuation.get('operating_margin'))}",
                f"Tax Rate: {pct(valuation.get('tax_rate'))}",
                f"Projection Years: {valuation.get('projection_years', 'N/A')}",
                "",
                "-" * 40,
                "ANALYSIS NARRATIVE",
                "-" * 40,
                valuation.get('narrative') or "N/A",
                "",
                "=" * 60,
                "Report Generated by DCF Valuation System",
                "=" * 60,
            ]
            
            content = "\n".join(lines)
            filename = f"{filename_prefix}.txt"
            
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type='text/plain',
                headers={'Content-Disposition': f"attachment; filename*=UTF-8''{filename}"}
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'json' or 'txt'")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
