from __future__ import annotations

import shutil
import uuid
import logging

from fastapi import APIRouter, HTTPException, UploadFile

from backend.config import UPLOAD_DIR
from backend.models.schemas import ExtractionResponse
from backend.models.error_models import ErrorResponse, validation_error, not_found_error
from backend.services.pdf_service import extract_text_from_pdf
from backend.services import extractor_service
from backend.exceptions import DCFException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("/upload", response_model=ExtractionResponse)
async def upload_and_extract(
    file: UploadFile,
    company_name: str | None = None,
    ticker: str | None = None,
    use_rag: bool = True,
    use_web_search: bool = True
):
    """
    Upload a PDF, extract text, then use LLM to extract financial data.
    
    Args:
        file: PDF file
        company_name: Company name for RAG context
        ticker: Stock ticker for RAG context
        use_rag: Enable RAG retrieval (database + web search)
        use_web_search: Allow web search if database empty
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOAD_DIR / safe_name

    try:
        with dest.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)

        text = extract_text_from_pdf(str(dest))
        if not text.strip():
            return ExtractionResponse(
                success=False,
                error="Could not extract text from PDF.",
            )

        return await extractor_service.extract_from_text(
            text=text,
            company_name=company_name,
            ticker=ticker,
            use_rag=use_rag,
            use_web_search=use_web_search
        )
    except Exception as exc:
        return ExtractionResponse(success=False, error=str(exc))
    finally:
        if dest.exists():
            dest.unlink()


@router.post("/text", response_model=ExtractionResponse)
async def extract_from_text(payload: dict):
    """Extract financial data from raw text using LLM."""
    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")
    try:
        return await extractor_service.extract_from_text(text)
    except Exception as exc:
        return ExtractionResponse(success=False, error=str(exc))
