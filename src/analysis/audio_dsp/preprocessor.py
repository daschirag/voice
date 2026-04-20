import os
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np
import soundfile as sf
import ffmpeg
from df.enhance import enhance, init_df, load_audio, save_audio

from src.core.config import settings
from src.core.logger import logger


@dataclass
class AudioMetadata:
    original_path: str
    processed_path: str
    original_format: str
    duration_seconds: float
    sample_rate: int
    channels: int
    estimated_snr_db: float
    denoising_applied: bool
    file_size_bytes: int


@dataclass
class PreprocessingResult:
    success: bool
    audio_path: str
    metadata: Optional[AudioMetadata] = None
    error_message: Optional[str] = None


def _estimate_snr(audio: np.ndarray, sample_rate: int) -> float:
    frame_size = int(sample_rate * 0.02)
    if len(audio) < frame_size * 2:
        return 30.0
    frames = [
        audio[i:i + frame_size]
        for i in range(0, len(audio) - frame_size, frame_size)
    ]
    rms_values = np.array([
        np.sqrt(np.mean(f ** 2)) for f in frames if len(f) == frame_size
    ])
    if len(rms_values) == 0:
        return 30.0
    sorted_rms = np.sort(rms_values)
    n = max(1, len(sorted_rms) // 10)
    noise_rms = np.mean(sorted_rms[:n]) + 1e-10
    signal_rms = np.mean(sorted_rms[-n:]) + 1e-10
    snr_db = 20 * np.log10(signal_rms / noise_rms)
    return float(np.clip(snr_db, 0, 60))


def _peak_normalize(audio: np.ndarray, target_dbfs: float = -3.0) -> np.ndarray:
    peak = np.max(np.abs(audio))
    if peak < 1e-10:
        logger.warning("Audio appears to be silent - peak amplitude near zero")
        return audio
    target_linear = 10 ** (target_dbfs / 20.0)
    return audio * (target_linear / peak)


def _convert_with_ffmpeg(
    input_path: str,
    output_path: str,
    target_sr: int = 16000,
) -> bool:
    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                ar=target_sr,
                ac=1,
                acodec="pcm_s16le"
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return True
    except ffmpeg.Error as e:
        logger.error(f"ffmpeg conversion failed: {e.stderr.decode() if e.stderr else str(e)}")
        return False


def _apply_deepfilternet(
    input_wav_path: str,
    output_wav_path: str,
    target_sr: int = 16000,
) -> bool:
    """
    Apply DeepFilterNet denoising.
    DeepFilterNet works internally at 48kHz.
    After enhancement, we resample back to target_sr (16kHz) using ffmpeg.
    """
    try:
        # Temp file for DeepFilterNet 48kHz output
        temp_48k = input_wav_path.replace(".wav", "_48k.wav")

        model, df_state, _ = init_df()
        audio, _ = load_audio(input_wav_path, sr=df_state.sr())
        enhanced = enhance(model, df_state, audio)
        save_audio(temp_48k, enhanced, df_state.sr())

        # Resample from 48kHz back to 16kHz using ffmpeg
        success = _convert_with_ffmpeg(temp_48k, output_wav_path, target_sr)

        # Clean up 48kHz temp file
        if os.path.exists(temp_48k):
            os.remove(temp_48k)

        return success

    except Exception as e:
        logger.error(f"DeepFilterNet enhancement failed: {e}")
        return False


def preprocess_audio(
    input_path: str,
    output_dir: Optional[str] = None,
    job_id: Optional[str] = None,
) -> PreprocessingResult:
    """
    Main preprocessing pipeline.
    Converts any audio to clean 16kHz mono WAV ready for ASR.

    Steps:
      1. Validate input file
      2. ffmpeg: convert to 16kHz mono WAV
      3. Load into numpy array
      4. Estimate SNR
      5. DeepFilterNet: denoise if SNR below threshold, resample back to 16kHz
      6. Peak normalize to -3 dBFS
      7. Save final WAV
      8. Return result with metadata
    """
    input_path = str(input_path)
    job_id = job_id or str(uuid.uuid4())[:8]

    # Step 0: Validate input
    if not os.path.exists(input_path):
        return PreprocessingResult(
            success=False,
            audio_path="",
            error_message=f"Input file not found: {input_path}"
        )

    supported_formats = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
    file_ext = Path(input_path).suffix.lower()
    if file_ext not in supported_formats:
        return PreprocessingResult(
            success=False,
            audio_path="",
            error_message=f"Unsupported format: {file_ext}"
        )

    # Step 1: Set up output paths
    if output_dir is None:
        output_dir = str(settings.upload_dir)
    os.makedirs(output_dir, exist_ok=True)

    ffmpeg_output = os.path.join(output_dir, f"{job_id}_raw.wav")
    final_output = os.path.join(output_dir, f"{job_id}_processed.wav")

    logger.info(f"[{job_id}] Starting preprocessing: {Path(input_path).name}")

    # Step 2: ffmpeg conversion to 16kHz mono WAV
    logger.debug(f"[{job_id}] Converting to 16kHz mono WAV via ffmpeg")
    if not _convert_with_ffmpeg(input_path, ffmpeg_output, settings.target_sample_rate):
        return PreprocessingResult(
            success=False,
            audio_path="",
            error_message="ffmpeg conversion failed. Check if ffmpeg is installed."
        )

    # Step 3: Load audio into numpy
    try:
        audio, sample_rate = sf.read(ffmpeg_output, dtype="float32")
    except Exception as e:
        return PreprocessingResult(
            success=False,
            audio_path="",
            error_message=f"Failed to read converted WAV: {e}"
        )

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    duration_seconds = len(audio) / sample_rate
    file_size = os.path.getsize(input_path)

    logger.info(f"[{job_id}] Duration: {duration_seconds:.1f}s | SR: {sample_rate}Hz")

    # Step 4: Estimate SNR
    snr_db = _estimate_snr(audio, sample_rate)
    logger.info(f"[{job_id}] Estimated SNR: {snr_db:.1f} dB")

    # Step 5: Conditional denoising
    denoising_applied = False
    if snr_db < settings.denoise_skip_snr_db:
        logger.info(f"[{job_id}] SNR below {settings.denoise_skip_snr_db}dB - applying DeepFilterNet")
        # _apply_deepfilternet now handles 48k->16k resampling internally
        denoise_success = _apply_deepfilternet(
            ffmpeg_output,
            ffmpeg_output,
            target_sr=settings.target_sample_rate
        )
        if denoise_success:
            # Reload the 16kHz denoised audio
            audio, sample_rate = sf.read(ffmpeg_output, dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)
            denoising_applied = True
            logger.info(f"[{job_id}] Denoising complete - SR: {sample_rate}Hz")
        else:
            logger.warning(f"[{job_id}] Denoising failed - continuing with original audio")
    else:
        logger.info(f"[{job_id}] SNR sufficient - skipping denoising")

    # Step 6: Peak normalize to -3 dBFS
    audio = _peak_normalize(audio, target_dbfs=settings.peak_normalize_dbfs)
    logger.debug(f"[{job_id}] Normalized to {settings.peak_normalize_dbfs} dBFS")

    # Step 7: Save final processed WAV
    try:
        sf.write(final_output, audio, sample_rate, subtype="PCM_16")
    except Exception as e:
        return PreprocessingResult(
            success=False,
            audio_path="",
            error_message=f"Failed to save processed WAV: {e}"
        )

    # Clean up intermediate file
    if os.path.exists(ffmpeg_output) and ffmpeg_output != final_output:
        os.remove(ffmpeg_output)

    # Step 8: Build result
    metadata = AudioMetadata(
        original_path=input_path,
        processed_path=final_output,
        original_format=file_ext,
        duration_seconds=duration_seconds,
        sample_rate=sample_rate,
        channels=1,
        estimated_snr_db=snr_db,
        denoising_applied=denoising_applied,
        file_size_bytes=file_size,
    )

    logger.success(f"[{job_id}] Preprocessing complete -> {Path(final_output).name}")

    return PreprocessingResult(
        success=True,
        audio_path=final_output,
        metadata=metadata,
    )