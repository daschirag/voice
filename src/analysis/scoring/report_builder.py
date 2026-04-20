"""
Report Builder
--------------
Assembles all analysis results into a structured report object.
This object is then rendered as JSON, PDF, or HTML.
"""
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.analysis.scoring.composite import CompositeResult
from src.analysis.asr.transcriber import TranscriptResult
from src.analysis.audio_dsp.preprocessor import AudioMetadata
from src.core.logger import logger


@dataclass
class ReportMetadata:
    job_id: str
    filename: str
    duration_seconds: float
    language: str
    role: str
    generated_at: str
    asr_confidence: float
    used_fallback: bool


@dataclass
class SASReport:
    """
    Complete Speech Analysis Report.
    Single object that can be serialized to JSON or rendered to PDF/HTML.
    """
    metadata: ReportMetadata
    composite_score: float
    composite_pct: float
    grade: str
    summary: str
    improvement_priorities: List[str]
    dimensions: Dict[str, Any]
    transcript: str
    low_confidence_words: List[dict]


def build_report(
    composite: CompositeResult,
    asr_result: TranscriptResult,
    audio_metadata: AudioMetadata,
    job_id: Optional[str] = None,
    role: str = "general",
) -> SASReport:
    """
    Assemble all analysis results into one SASReport object.
    """
    job_id = job_id or str(uuid.uuid4())[:8]

    metadata = ReportMetadata(
        job_id=job_id,
        filename=Path(audio_metadata.original_path).name,
        duration_seconds=round(audio_metadata.duration_seconds, 1),
        language=asr_result.language,
        role=role,
        generated_at=datetime.now(timezone.utc).isoformat(),
        asr_confidence=round(asr_result.mean_confidence, 3),
        used_fallback=asr_result.used_fallback,
    )

    # Serialize dimensions to plain dicts
    dimensions_dict = {}
    for key, dim in composite.dimensions.items():
        dimensions_dict[key] = {
            "name": dim.name,
            "score": dim.raw_score,
            "normalized": round(dim.normalized, 3),
            "insight": dim.insight,
            "metrics": dim.raw_metrics,
        }

    report = SASReport(
        metadata=metadata,
        composite_score=composite.composite_score,
        composite_pct=composite.composite_pct,
        grade=composite.grade,
        summary=composite.summary,
        improvement_priorities=composite.improvement_priorities,
        dimensions=dimensions_dict,
        transcript=asr_result.transcript,
        low_confidence_words=asr_result.low_confidence_words[:10] if asr_result.low_confidence_words else [],
    )

    logger.info(f"[{job_id}] Report built: {composite.composite_score}/5 Grade {composite.grade}")
    return report


def report_to_dict(report: SASReport) -> dict:
    """Convert SASReport to a plain dict for JSON serialization."""
    return {
        "metadata": {
            "job_id": report.metadata.job_id,
            "filename": report.metadata.filename,
            "duration_seconds": report.metadata.duration_seconds,
            "language": report.metadata.language,
            "role": report.metadata.role,
            "generated_at": report.metadata.generated_at,
            "asr_confidence": report.metadata.asr_confidence,
            "used_fallback": report.metadata.used_fallback,
        },
        "results": {
            "composite_score": report.composite_score,
            "composite_pct": report.composite_pct,
            "grade": report.grade,
            "summary": report.summary,
            "improvement_priorities": report.improvement_priorities,
        },
        "dimensions": report.dimensions,
        "transcript": report.transcript,
        "low_confidence_words": [
            {
                "word": w.word if hasattr(w, "word") else w.get("word", ""),
                "start": w.start if hasattr(w, "start") else w.get("start", 0),
                "end": w.end if hasattr(w, "end") else w.get("end", 0),
                "confidence": w.confidence if hasattr(w, "confidence") else w.get("confidence", 0),
            }
            for w in report.low_confidence_words
        ],
    }


def save_json_report(report: SASReport, output_dir: str) -> str:
    """Save report as JSON file. Returns path to saved file."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{report.metadata.job_id}_report.json")

    report_dict = report_to_dict(report)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    logger.info(f"JSON report saved: {output_path}")
    return output_path