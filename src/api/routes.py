import os
import uuid
import shutil
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from src.core.config import settings
from src.core.logger import logger
from src.api.schemas import (
    JobSubmittedResponse, JobStatusResponse, AnalysisResultResponse,
    HealthResponse, JobStatus, RoleEnum
)

router = APIRouter(prefix="/api/v1", tags=["Speech Analysis"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}

# In-memory job store (dev mode - no Redis needed)
_job_store = {}


def _run_pipeline(audio_path: str, job_id: str, role: str, original_filename: str):
    """Run the full analysis pipeline synchronously."""
    try:
        _job_store[job_id] = {"status": "progress", "stage": "preprocessing", "progress": 10}

        from src.analysis.audio_dsp.preprocessor import preprocess_audio
        pre = preprocess_audio(input_path=audio_path, job_id=job_id)
        if not pre.success:
            raise ValueError(f"Preprocessing failed: {pre.error_message}")

        _job_store[job_id] = {"status": "progress", "stage": "transcription", "progress": 30}
        from src.analysis.asr.transcriber import transcribe
        asr = transcribe(pre.audio_path, job_id)
        if not asr.success:
            raise ValueError(f"ASR failed: {asr.error_message}")

        _job_store[job_id] = {"status": "progress", "stage": "vad", "progress": 50}
        from src.analysis.audio_dsp.vad import analyze_vad
        vad = analyze_vad(pre.audio_path, job_id)

        _job_store[job_id] = {"status": "progress", "stage": "analysis", "progress": 65}
        from src.analysis.nlp.clarity import analyze_clarity
        from src.analysis.nlp.filler_words import analyze_filler_words
        from src.analysis.nlp.pauses import analyze_pauses
        from src.analysis.nlp.punctuation import analyze_punctuation
        from src.analysis.nlp.language_quality import analyze_language_quality
        from src.analysis.nlp.delivery import analyze_delivery
        from src.analysis.nlp.tone import analyze_tone

        clarity  = analyze_clarity(asr.words, job_id)
        filler   = analyze_filler_words(asr.words, asr.transcript, job_id=job_id)
        pauses   = analyze_pauses(vad, job_id)
        punct    = analyze_punctuation(asr.transcript, asr.words, vad, job_id)
        language = analyze_language_quality(asr.transcript, job_id)
        delivery = analyze_delivery(asr.words, vad, job_id)
        tone     = analyze_tone(pre.audio_path, asr.transcript, delivery.rhythm_variance, job_id)

        _job_store[job_id] = {"status": "progress", "stage": "scoring", "progress": 85}
        from src.analysis.scoring.normalizer import build_dimension_scores
        from src.analysis.scoring.composite import calculate_composite
        from src.analysis.scoring.report_builder import build_report
        from src.analysis.scoring.generator import generate_all_reports
        from src.analysis.scoring.report_builder import report_to_dict

        dims      = build_dimension_scores(clarity, filler, pauses, punct, language, delivery, tone)
        composite = calculate_composite(dims, role=role, job_id=job_id)
        report    = build_report(composite, asr, pre.metadata, job_id=job_id, role=role)

        _job_store[job_id] = {"status": "progress", "stage": "reports", "progress": 95}
        generate_all_reports(report, output_dir=str(settings.reports_dir))

        # Clean up processed audio
        if os.path.exists(pre.audio_path):
            os.remove(pre.audio_path)

        _job_store[job_id] = {
            "status": "completed",
            "progress": 100,
            "report": report_to_dict(report),
        }
        logger.success(f"[{job_id}] Pipeline complete")

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}")
        _job_store[job_id] = {"status": "failed", "error": str(e)}


@router.post("/analyze", response_model=JobSubmittedResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    role: RoleEnum = Form(default=RoleEnum.general),
):
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file_ext}")

    job_id = str(uuid.uuid4())[:12]
    upload_dir = str(settings.upload_dir)
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f"{job_id}_original{file_ext}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
    logger.info(f"[{job_id}] Uploaded: {file.filename} ({file_size_mb:.1f} MB)")

    # Run pipeline synchronously (dev mode - no Celery/RabbitMQ needed)
    _job_store[job_id] = {"status": "pending", "progress": 0}
    _run_pipeline(save_path, job_id, role.value, file.filename)

    return JobSubmittedResponse(
        job_id=job_id,
        status=_job_store[job_id]["status"],
        message=f"Analysis complete. GET /api/v1/report/{job_id}",
        filename=file.filename,
        role=role.value,
        estimated_seconds=0,
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    # Check in-memory store first
    if job_id in _job_store:
        job = _job_store[job_id]
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(job["status"]),
            stage=job.get("stage"),
            progress=job.get("progress", 0),
            message=job.get("message", ""),
            error=job.get("error"),
        )

    # Check if report file exists on disk
    report_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.json")
    if os.path.exists(report_path):
        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus.completed,
            progress=100,
            message="Report available",
        )

    raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.get("/report/{job_id}")
async def get_report(job_id: str):
    # Check in-memory store
    if job_id in _job_store and _job_store[job_id].get("report"):
        return JSONResponse(content=_job_store[job_id]["report"])

    # Check disk
    report_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))

    raise HTTPException(status_code=404, detail=f"Report not found for job {job_id}")


@router.get("/report/{job_id}/html")
async def get_html_report(job_id: str):
    html_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="HTML report not found")
    return FileResponse(path=html_path, media_type="text/html",
                        filename=f"speech_report_{job_id}.html")


@router.get("/report/{job_id}/pdf")
async def get_pdf_report(job_id: str):
    pdf_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(path=pdf_path, media_type="application/pdf",
                        filename=f"speech_report_{job_id}.pdf")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    import torch
    from src.analysis.asr.circuit_breaker import get_circuit_breaker
    from src.analysis.audio_dsp import vad as vad_module
    from src.analysis.asr import transcriber as asr_module
    from src.analysis.nlp import punctuation as punct_module

    gpu_available = torch.cuda.is_available()
    circuit = get_circuit_breaker()

    return HealthResponse(
        status="healthy",
        gpu_available=gpu_available,
        gpu_name=torch.cuda.get_device_name(0) if gpu_available else None,
        models_loaded={
            "whisper": asr_module._whisper_model is not None,
            "silero_vad": vad_module._silero_model is not None,
            "spacy": punct_module._nlp is not None,
        },
        circuit_breaker=circuit.get_status(),
    )


@router.get("/roles")
async def list_roles():
    from src.analysis.scoring.weights import ROLE_WEIGHTS
    return {
        "roles": list(ROLE_WEIGHTS.keys()),
        "default": "general",
        "descriptions": {
            "general":   "Equal weights across all dimensions",
            "sales":     "Emphasizes delivery, pauses, and tone",
            "executive": "Emphasizes clarity, language quality, filler words",
            "interview": "Balanced with emphasis on clarity and language",
            "coaching":  "Even development weighting for all dimensions",
        }
    }