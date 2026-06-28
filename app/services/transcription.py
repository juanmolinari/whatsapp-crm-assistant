from pathlib import Path


def transcribe_audio(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".txt")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8")
    return (
        f"[Transcripción simulada del archivo {path.name}] "
        "Instalá faster-whisper o agregá un .txt con el mismo nombre para transcripción local real."
    )
