import os
import sys
import warnings

# Must be set before any other imports
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

warnings.filterwarnings("ignore", message=".*torchaudio.backend.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*sinc_interpolation.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, module="df")
warnings.filterwarnings("ignore", category=UserWarning, module="lexical_diversity")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from src.core.config import settings
from src.core.logger import logger
from src.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Speech Analysis System v1.0...")

    for d in [settings.upload_dir, settings.reports_dir, settings.models_dir]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Pre-warm ASR
    try:
        from src.analysis.asr.transcriber import _get_whisper_model
        _get_whisper_model()
        logger.success("ASR model ready (GPU)")
    except Exception as e:
        logger.warning(f"ASR pre-warm failed: {e}")

    # Pre-warm VAD
    try:
        from src.analysis.audio_dsp.vad import _get_silero_model
        _get_silero_model()
        logger.success("VAD model ready")
    except Exception as e:
        logger.warning(f"VAD pre-warm failed: {e}")

    # Pre-warm spaCy
    try:
        from src.analysis.nlp.punctuation import _get_nlp
        _get_nlp()
        logger.success("spaCy model ready")
    except Exception as e:
        logger.warning(f"spaCy pre-warm failed: {e}")

    # Pre-warm RoBERTa sentiment
    try:
        from src.analysis.nlp.tone import _get_sentiment_pipeline
        _get_sentiment_pipeline()
        logger.success("Sentiment model ready")
    except Exception as e:
        logger.warning(f"Sentiment pre-warm failed: {e}")

    logger.success("=" * 50)
    logger.success("  Speech Analysis System READY")
    logger.success("  Docs  : http://localhost:8000/docs")
    logger.success("  Health: http://localhost:8000/api/v1/health")
    logger.success("=" * 50)
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Speech Analysis System",
    description=(
        "Evaluates recorded speech across 7 dimensions: "
        "Clarity, Filler Words, Pauses, Punctuation, "
        "Language Quality, Delivery, and Tone/Demeanor."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reports_dir = Path(settings.reports_dir)
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

app.include_router(router)


@app.get("/")
async def root():
    return {
        "name": "Speech Analysis System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "analyze": "POST /api/v1/analyze",
        "roles": "/api/v1/roles",
    }