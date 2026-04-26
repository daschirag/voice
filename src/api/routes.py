import os
import uuid
import shutil
import json
import pymongo
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from fastapi import (
    APIRouter, UploadFile, File, Form,
    HTTPException, Depends
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from src.core.config import settings
from src.core.logger import logger
from src.db.mongodb import get_db
from src.api.auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, get_current_admin, get_verified_user
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
_job_store = {}


def _serialize(doc: dict) -> dict:
    if doc is None:
        return {}
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


def _save_to_mongo(analysis_doc: dict):
    try:
        sync_client = pymongo.MongoClient(settings.mongodb_uri)
        sync_db = sync_client[settings.mongodb_db_name]
        sync_db.analyses.insert_one(analysis_doc)
        sync_client.close()
        logger.success(f"[{analysis_doc['job_id']}] Analysis saved to MongoDB")
    except Exception as e:
        logger.warning(f"MongoDB save warning: {e}")


def _run_pipeline(audio_path, job_id, role, user_id, username, email, original_filename):
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
        from src.analysis.scoring.report_builder import build_report, report_to_dict
        from src.analysis.scoring.generator import generate_all_reports

        dims      = build_dimension_scores(clarity, filler, pauses, punct, language, delivery, tone)
        composite = calculate_composite(dims, role=role, job_id=job_id)
        report    = build_report(composite, asr, pre.metadata, job_id=job_id, role=role)

        _job_store[job_id] = {"status": "progress", "stage": "reports", "progress": 95}
        report_paths = generate_all_reports(report, output_dir=str(settings.reports_dir))

        if os.path.exists(pre.audio_path):
            os.remove(pre.audio_path)

        report_dict = report_to_dict(report)

        # Save to MongoDB using sync pymongo
        analysis_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "username": username,
            "email": email,
            "filename": original_filename,
            "duration_seconds": pre.metadata.duration_seconds if pre.metadata else 0,
            "role": role,
            "recorded_at": datetime.now(timezone.utc),
            "composite_score": composite.composite_score,
            "composite_pct": composite.composite_pct,
            "grade": composite.grade,
            "summary": composite.summary,
            "improvement_priorities": composite.improvement_priorities,
            "dimensions": {
                k: {"name": v.name, "score": v.raw_score, "insight": v.insight, "metrics": v.raw_metrics}
                for k, v in dims.items()
            },
            "transcript": asr.transcript,
            "report_paths": report_paths,
            "asr_confidence": asr.mean_confidence,
        }
        _save_to_mongo(analysis_doc)

        _job_store[job_id] = {
            "status": "completed",
            "progress": 100,
            "report": report_dict,
        }
        logger.success(f"[{job_id}] Pipeline complete")

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}")
        _job_store[job_id] = {"status": "failed", "error": str(e)}


# AUTH ROUTES

@router.post("/auth/register")
async def register(
    full_name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    db = get_db()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    user_doc = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "mobile": mobile,
        "hashed_password": hash_password(password),
        "role": "client",
        "is_verified": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    }
    await db.users.insert_one(user_doc)
    logger.info(f"New client registered: {username} ({email})")
    return {
        "message": "Registration successful. Please wait for admin verification before logging in.",
        "username": username,
        "email": email,
    }


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.get("is_verified") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Your account is pending admin verification.")
    token = create_access_token({"sub": str(user["_id"])})
    logger.info(f"User logged in: {user['username']} (role: {user['role']})")
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
    }


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return _serialize(current_user)


# CLIENT ROUTES

@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    role: str = Form(default="general"),
    current_user: dict = Depends(get_verified_user),
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
    logger.info(f"[{job_id}] Uploaded by {current_user['username']}: {file.filename} ({file_size_mb:.1f} MB)")

    _job_store[job_id] = {"status": "pending", "progress": 0}
    _run_pipeline(
        save_path, job_id, role,
        user_id=str(current_user["_id"]),
        username=current_user["username"],
        email=current_user["email"],
        original_filename=file.filename,
    )

    return {
        "job_id": job_id,
        "status": _job_store[job_id]["status"],
        "message": f"Analysis complete. GET /api/v1/report/{job_id}",
        "filename": file.filename,
        "role": role,
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str, current_user: dict = Depends(get_current_user)):
    if job_id in _job_store:
        job = _job_store[job_id]
        return {
            "job_id": job_id,
            "status": job["status"],
            "stage": job.get("stage"),
            "progress": job.get("progress", 0),
            "message": job.get("message", ""),
            "error": job.get("error"),
        }
    report_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.json")
    if os.path.exists(report_path):
        return {"job_id": job_id, "status": "completed", "progress": 100}
    raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.get("/report/{job_id}")
async def get_report(job_id: str, current_user: dict = Depends(get_current_user)):
    if job_id in _job_store and _job_store[job_id].get("report"):
        return JSONResponse(content=_job_store[job_id]["report"])
    report_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.json")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/report/{job_id}/pdf")
async def get_pdf_report(job_id: str):
    pdf_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(path=pdf_path, media_type="application/pdf",
                        filename=f"speech_report_{job_id}.pdf")


@router.get("/report/{job_id}/html")
async def get_html_report(job_id: str):
    html_path = os.path.join(str(settings.reports_dir), f"{job_id}_report.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="HTML report not found")
    return FileResponse(path=html_path, media_type="text/html")


@router.get("/my-reports")
async def get_my_reports(current_user: dict = Depends(get_verified_user)):
    db = get_db()
    cursor = db.analyses.find(
        {"user_id": str(current_user["_id"])},
        sort=[("recorded_at", -1)]
    )
    docs = await cursor.to_list(length=100)
    return [_serialize(d) for d in docs]


# ADMIN ROUTES

@router.get("/admin/users")
async def get_all_users(admin: dict = Depends(get_current_admin)):
    db = get_db()
    cursor = db.users.find({}, sort=[("created_at", -1)])
    users = await cursor.to_list(length=500)
    return [_serialize(u) for u in users]


@router.put("/admin/verify/{user_id}")
async def verify_user(user_id: str, admin: dict = Depends(get_current_admin)):
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_verified": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Admin {admin['username']} verified user {user_id}")
    return {"message": "User verified successfully", "user_id": user_id}


@router.put("/admin/unverify/{user_id}")
async def unverify_user(user_id: str, admin: dict = Depends(get_current_admin)):
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_verified": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User unverified", "user_id": user_id}


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_current_admin)):
    db = get_db()
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted", "user_id": user_id}


@router.get("/admin/reports")
async def get_all_reports(
    admin: dict = Depends(get_current_admin),
    username: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    db = get_db()
    query = {}
    if username:
        query["username"] = {"$regex": username, "$options": "i"}
    if date_from:
        query.setdefault("recorded_at", {})["$gte"] = datetime.fromisoformat(date_from)
    if date_to:
        query.setdefault("recorded_at", {})["$lte"] = datetime.fromisoformat(date_to)
    cursor = db.analyses.find(query, sort=[("recorded_at", -1)])
    docs = await cursor.to_list(length=1000)
    return [_serialize(d) for d in docs]


@router.get("/admin/stats")
async def get_stats(admin: dict = Depends(get_current_admin)):
    db = get_db()
    total_users = await db.users.count_documents({"role": "client"})
    verified_users = await db.users.count_documents({"role": "client", "is_verified": True})
    pending_users = await db.users.count_documents({"role": "client", "is_verified": False})
    total_analyses = await db.analyses.count_documents({})
    pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$composite_score"}}}]
    avg_result = await db.analyses.aggregate(pipeline).to_list(1)
    avg_score = round(avg_result[0]["avg"], 2) if avg_result else 0
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "pending_users": pending_users,
        "total_analyses": total_analyses,
        "avg_composite_score": avg_score,
    }


# SYSTEM ROUTES

@router.get("/health")
async def health_check():
    import torch
    from src.analysis.asr.circuit_breaker import get_circuit_breaker
    from src.analysis.audio_dsp import vad as vad_module
    from src.analysis.asr import transcriber as asr_module
    from src.analysis.nlp import punctuation as punct_module

    gpu_available = torch.cuda.is_available()
    circuit = get_circuit_breaker()
    db_ok = False
    try:
        db = get_db()
        if db is not None:
            await db.command("ping")
            db_ok = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
        "mongodb_connected": db_ok,
        "models_loaded": {
            "whisper": asr_module._whisper_model is not None,
            "silero_vad": vad_module._silero_model is not None,
            "spacy": punct_module._nlp is not None,
        },
        "circuit_breaker": circuit.get_status(),
    }


@router.get("/roles")
async def list_roles():
    from src.analysis.scoring.weights import ROLE_WEIGHTS
    return {
        "roles": list(ROLE_WEIGHTS.keys()),
        "default": "general",
        "descriptions": {
            "general": "Equal weights across all dimensions",
            "sales": "Emphasizes delivery, pauses, and tone",
            "executive": "Emphasizes clarity, language quality, filler words",
            "interview": "Balanced with emphasis on clarity and language",
            "coaching": "Even development weighting for all dimensions",
        }
    }

