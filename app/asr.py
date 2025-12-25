# backend/app/asr.py
import os
import tempfile
import asyncio
from typing import Dict, Any, List

# Attempt to import faster-whisper but do NOT raise during import; support lazy init
HAS_FASTER_WHISPER = True
try:
    from faster_whisper import WhisperModel
except Exception:
    HAS_FASTER_WHISPER = False

# ===============================
# CONFIG (SAFE DEFAULTS)
# ===============================

WHISPER_DEVICE = "cpu" # cpu is safest
WHISPER_MODEL_PATH = "tiny"

# IMPORTANT: int8 is best for CPU, float16 ONLY for CUDA
COMPUTE_TYPE = "int8"
MODEL: WhisperModel | None = None


# ===============================
# MODEL INIT
# ===============================

def init_model(device_preference: str = None, model_path: str = None, compute_type: str = None):
    global MODEL, WHISPER_DEVICE, WHISPER_MODEL_PATH, COMPUTE_TYPE

    if not HAS_FASTER_WHISPER:
        print("[asr] faster-whisper not installed; ASR disabled.")
        return

    WHISPER_DEVICE = "cpu"
    WHISPER_MODEL_PATH = "tiny"
    COMPUTE_TYPE = "int8"

    try:
        print(f"[asr] initializing whisper model from: {WHISPER_MODEL_PATH} device={WHISPER_DEVICE} compute_type={COMPUTE_TYPE}")
        MODEL = WhisperModel(
            WHISPER_MODEL_PATH,
            device=WHISPER_DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        print("[asr] ASR model initialized successfully")
    except Exception as e:
        print("[asr] ASR completely unavailable:", e)
        MODEL = None

# ===============================
# TRANSCRIPTION
# ===============================

async def transcribe_bytes(contents: bytes, filename: str = "upload") -> Dict[str, Any]:
    """
    Transcribe given audio bytes.
    Gracefully degrades if ASR unavailable.
    """
    if MODEL is None:
        return {
            "text": f"[Audio uploaded: {filename} | {len(contents)} bytes]\n\n⚠️ Automatic transcription is currently unavailable.",
            "segments": [],
            "duration_seconds": 0.0,
        }

    suffix = os.path.splitext(filename)[-1] or ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        tf.write(contents)
        tmp_path = tf.name

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _sync_transcribe, tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return result


def _sync_transcribe(path: str) -> Dict[str, Any]:
    """
    Blocking whisper call (runs in executor).
    """
    segments = []

    transcribe_result = MODEL.transcribe(
        path,
        beam_size=5,
        language=None,
        vad_filter=False,
    )

    if isinstance(transcribe_result, tuple) and len(transcribe_result) == 2:
        seg_iter, _info = transcribe_result
    else:
        seg_iter = transcribe_result

    full_text_parts: List[str] = []

    for seg in seg_iter:
        start = float(getattr(seg, "start", 0.0))
        end = float(getattr(seg, "end", 0.0))
        text = str(getattr(seg, "text", "")).strip()

        if text:
            segments.append({"start": start, "end": end, "text": text})
            full_text_parts.append(text)

    full_text = " ".join(full_text_parts).strip()
    duration_seconds = max((s["end"] for s in segments), default=0.0)

    return {
        "text": full_text,
        "segments": segments,
        "duration_seconds": duration_seconds,
    }
