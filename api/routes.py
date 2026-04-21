"""FastAPI routes."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from main import build_pipeline

router = APIRouter()
pipeline = build_pipeline()


@router.get("/health")
def health() -> dict:
    """Liveness endpoint."""
    return {"status": "ok"}


@router.post("/adjudicate")
async def adjudicate(files: list[UploadFile] = File(...), detailed: bool = Query(default=True)) -> dict:
    """Upload claim documents and receive adjudication JSON."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    started = perf_counter()
    upload_dir = Path("data/input/api_uploads") / datetime.utcnow().strftime("%Y%m%d%H%M%S")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_paths: list[str] = []
    for file in files:
        target = upload_dir / file.filename
        content = await file.read()
        target.write_bytes(content)
        file_paths.append(str(target))
    payload = pipeline.run(file_paths)
    response = {
        "request": {
            "uploaded_files": [Path(path).name for path in file_paths],
            "file_count": len(file_paths),
        },
        "processing": {
            "response_time_ms": round((perf_counter() - started) * 1000, 2),
            "status": payload["decision"]["status"],
            "confidence": payload["decision"]["confidence"],
        },
    }
    if detailed:
        response["result"] = payload
    else:
        response["result"] = {
            "claim_id": payload["claim_id"],
            "summary": payload.get("summary", {}),
            "decision": payload["decision"],
        }
    return response
