from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile

from config import UPLOAD_DIR
from models.schemas import ExtractionResponse
from services.pdf_service import extract_text_from_pdf
from services import extractor_service

router = APIRouter(prefix="/extract", tags=["extract"])


@router.post("/upload", response_model=ExtractionResponse)
async def upload_and_extract(file: UploadFile):
    """Upload a PDF, extract text, then use LLM to extract financial data."""
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

        return await extractor_service.extract_from_text(text)
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
