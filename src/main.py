import os
import warnings

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

warnings.filterwarnings("ignore", message=".*torchaudio.backend.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, module="df")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path

from src.core.config import settings
from src.core.logger import logger
from src.api.routes import router
from src.db.mongodb import connect_db, disconnect_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Speech Analysis System v2.0...")
    for d in [settings.upload_dir, settings.reports_dir, settings.models_dir]:
        Path(d).mkdir(parents=True, exist_ok=True)
    await connect_db()
    try:
        from src.analysis.asr.transcriber import _get_whisper_model
        _get_whisper_model()
        logger.success("ASR model ready (GPU)")
    except Exception as e:
        logger.warning(f"ASR pre-warm failed: {e}")
    try:
        from src.analysis.audio_dsp.vad import _get_silero_model
        _get_silero_model()
        logger.success("VAD model ready")
    except Exception as e:
        logger.warning(f"VAD pre-warm failed: {e}")
    try:
        from src.analysis.nlp.punctuation import _get_nlp
        _get_nlp()
        logger.success("spaCy model ready")
    except Exception as e:
        logger.warning(f"spaCy pre-warm failed: {e}")
    logger.success("=" * 50)
    logger.success("  Speech Analysis System v2.0 READY")
    logger.success("  Docs  : http://localhost:8000/docs")
    logger.success("  Health: http://localhost:8000/api/v1/health")
    logger.success("=" * 50)
    yield
    await disconnect_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Speech Analysis System",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

reports_dir = Path(settings.reports_dir)
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": "Speech Analysis System v2.0", "docs": "/docs"}