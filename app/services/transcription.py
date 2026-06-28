from pathlib import Path

from app.config import get_settings


def transcribe_audio(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".txt")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8")

    settings = get_settings()
    if settings.local_transcription_provider == "faster-whisper":
        return _transcribe_with_faster_whisper(path, settings.local_transcription_model)

    return (
        f"[Transcripción simulada del archivo {path.name}] "
        "Para transcripción real, configurá LOCAL_TRANSCRIPTION_PROVIDER=faster-whisper "
        "e instalá requirements-audio.txt."
    )


def _transcribe_with_faster_whisper(path: Path, model_name: str) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return (
            f"[No pude transcribir {path.name}: falta instalar faster-whisper. "
            "Ejecutá .\\.venv\\Scripts\\python.exe -m pip install -r requirements-audio.txt]"
        )

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), language="es", vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    return text or f"[No se detectó voz clara en {path.name}]"
