"""
Celery Tasks
------------
The full analysis pipeline wrapped as a Celery task.
FastAPI receives the upload, saves the file, enqueues this task,
and immediately returns job_id to the client.
The client polls /status/{job_id} until complete.
"""
import os
import json
import traceback
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from celery import Task
from src.core.celery_app import celery_app
from src.core.logger import logger
from src.core.config import settings


class AnalysisTask(Task):
    """Base task class with model caching."""
    abstract = True
    _models_loaded = False

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        logger.success(f"Task {task_id} completed successfully")


@celery_app.task(
    bind=True,
    base=AnalysisTask,
    name="src.workers.tasks.analyze_audio_task",
    max_retries=2,
    default_retry_delay=10,
)
def analyze_audio_task(
    self,
    audio_path: str,
    job_id: str,
    role: str = "general",
    original_filename: str = "unknown.wav",
):
    """
    Full speech analysis pipeline as a Celery task.

    Called by FastAPI after file upload.
    Updates task state at each stage for progress polling.

    States:
      PENDING   -> task queued
      STARTED   -> task running
      PROGRESS  -> intermediate updates
      SUCCESS   -> completed with result
      FAILURE   -> error occurred
    """
    try:
        # ── Stage 1: Preprocessing ────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "preprocessing", "progress": 10,
                  "job_id": job_id, "message": "Preprocessing audio..."}
        )
        logger.info(f"[{job_id}] Task started: {original_filename}")

        from src.analysis.audio_dsp.preprocessor import preprocess_audio
        pre_result = preprocess_audio(
            input_path=audio_path,
            job_id=job_id,
        )

        if not pre_result.success:
            raise ValueError(f"Preprocessing failed: {pre_result.error_message}")

        processed_path = pre_result.audio_path

        # ── Stage 2: ASR ──────────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "transcription", "progress": 30,
                  "job_id": job_id, "message": "Transcribing speech..."}
        )

        from src.analysis.asr.transcriber import transcribe
        asr_result = transcribe(processed_path, job_id)

        if not asr_result.success:
            raise ValueError(f"ASR failed: {asr_result.error_message}")

        # ── Stage 3: VAD ──────────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "vad", "progress": 50,
                  "job_id": job_id, "message": "Detecting speech patterns..."}
        )

        from src.analysis.audio_dsp.vad import analyze_vad
        vad_result = analyze_vad(processed_path, job_id)

        # ── Stage 4: Analysis Dimensions ─────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "analysis", "progress": 65,
                  "job_id": job_id, "message": "Analyzing 7 dimensions..."}
        )

        from src.analysis.nlp.clarity import analyze_clarity
        from src.analysis.nlp.filler_words import analyze_filler_words
        from src.analysis.nlp.pauses import analyze_pauses
        from src.analysis.nlp.punctuation import analyze_punctuation
        from src.analysis.nlp.language_quality import analyze_language_quality
        from src.analysis.nlp.delivery import analyze_delivery
        from src.analysis.nlp.tone import analyze_tone

        clarity  = analyze_clarity(asr_result.words, job_id)
        filler   = analyze_filler_words(asr_result.words, asr_result.transcript, job_id=job_id)
        pauses   = analyze_pauses(vad_result, job_id)
        punct    = analyze_punctuation(asr_result.transcript, asr_result.words, vad_result, job_id)
        language = analyze_language_quality(asr_result.transcript, job_id)
        delivery = analyze_delivery(asr_result.words, vad_result, job_id)
        tone     = analyze_tone(processed_path, asr_result.transcript, delivery.rhythm_variance, job_id)

        # ── Stage 5: Scoring ──────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "scoring", "progress": 85,
                  "job_id": job_id, "message": "Calculating scores..."}
        )

        from src.analysis.scoring.normalizer import build_dimension_scores
        from src.analysis.scoring.composite import calculate_composite
        from src.analysis.scoring.report_builder import build_report
        from src.analysis.scoring.generator import generate_all_reports

        dims      = build_dimension_scores(clarity, filler, pauses, punct, language, delivery, tone)
        composite = calculate_composite(dims, role=role, job_id=job_id)

        # ── Stage 6: Reports ──────────────────────────────────
        self.update_state(
            state="PROGRESS",
            meta={"stage": "reports", "progress": 95,
                  "job_id": job_id, "message": "Generating reports..."}
        )

        report = build_report(
            composite, asr_result, pre_result.metadata,
            job_id=job_id, role=role
        )

        report_paths = generate_all_reports(
            report,
            output_dir=str(settings.reports_dir)
        )

        # Clean up processed audio file (keep original upload)
        if os.path.exists(processed_path):
            os.remove(processed_path)

        logger.success(f"[{job_id}] Pipeline complete")

        # Return serializable result
        from src.analysis.scoring.report_builder import report_to_dict
        return {
            "job_id": job_id,
            "status": "completed",
            "report": report_to_dict(report),
            "report_paths": report_paths,
        }

    except Exception as exc:
        logger.error(f"[{job_id}] Task failed: {exc}\n{traceback.format_exc()}")
        # Retry on transient errors
        try:
            raise self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(exc),
            }