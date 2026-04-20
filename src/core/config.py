import os
import sys
import warnings

# Suppress all known harmless warnings
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

# Suppress Python warnings
warnings.filterwarnings("ignore", message=".*torchaudio.backend.*")
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*sinc_interpolation.*")
warnings.filterwarnings("ignore", message=".*cudnnException.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, module="df")
warnings.filterwarnings("ignore", category=UserWarning, module="lexical_diversity")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Suppress transformers verbose logging
try:
    import transformers
    transformers.logging.set_verbosity_error()
except Exception:
    pass

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = Field(default="development")
    secret_key: str = Field(default="dev-secret-change-in-production")

    # ASR
    asr_model: str = Field(default="faster-whisper")
    whisper_model_size: str = Field(default="small.en")
    whisper_device: str = Field(default="cuda")
    whisper_compute_type: str = Field(default="float16")

    # Circuit Breaker
    asr_confidence_threshold: float = Field(default=0.75)
    circuit_breaker_failure_count: int = Field(default=3)
    circuit_breaker_cooldown_seconds: int = Field(default=60)

    # Cloud Fallback
    deepgram_api_key: str = Field(default="")
    assemblyai_api_key: str = Field(default="")

    # Celery + RabbitMQ
    celery_broker_url: str = Field(default="amqp://guest:guest@localhost:5672//")
    celery_result_backend: str = Field(default="redis://localhost:6379/0")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Database
    database_url: str = Field(default="postgresql://sas_user:sas_pass@localhost:5432/sas_db")

    # Storage
    upload_dir: Path = Field(default=ROOT_DIR / "uploads")
    reports_dir: Path = Field(default=ROOT_DIR / "reports")
    models_dir: Path = Field(default=ROOT_DIR / "models")
    max_upload_duration_minutes: int = Field(default=60)

    # Audio Preprocessing
    target_sample_rate: int = Field(default=16000)
    peak_normalize_dbfs: float = Field(default=-3.0)
    min_pause_ms: int = Field(default=150)
    silence_trim_dbfs: float = Field(default=-50.0)
    denoise_skip_snr_db: float = Field(default=30.0)

    # Scoring
    default_role: str = Field(default="general")


settings = Settings()