import shutil
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.database import get_db, init_db
from app.services.excel import process_excel
from app.services.parser import parse_text, today_local
from app.services.repository import save_parsed_input, search_clients
from app.services.summary import generate_daily_summary
from app.services.transcription import transcribe_audio
from app.services.zero_cost import CostBlockedError, assert_zero_cost_allowed

settings = get_settings()
app = FastAPI(title="Asistente CRM Local $0")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    init_db()
    today = today_local()
    tasks_today = (
        db.query(models.Task)
        .filter(models.Task.status == "open", models.Task.due_date == today)
        .order_by(models.Task.priority.desc())
        .all()
    )
    overdue = (
        db.query(models.Task)
        .filter(models.Task.status == "open", models.Task.due_date < today)
        .order_by(models.Task.due_date.asc())
        .all()
    )
    notes = db.query(models.ClientNote).order_by(models.ClientNote.created_at.desc()).limit(15).all()
    opportunities = db.query(models.Opportunity).order_by(models.Opportunity.created_at.desc()).limit(15).all()
    summary = db.query(models.DailySummary).order_by(models.DailySummary.summary_date.desc()).first()
    unresolved = (
        db.query(models.UnresolvedEntity)
        .filter(models.UnresolvedEntity.resolved.is_(False))
        .order_by(models.UnresolvedEntity.created_at.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "settings": settings,
            "today": today,
            "tasks_today": tasks_today,
            "overdue": overdue,
            "notes": notes,
            "opportunities": opportunities,
            "summary": summary,
            "unresolved": unresolved,
        },
    )


@app.post("/text")
def ingest_text(text: str = Form(...), db: Session = Depends(get_db)):
    parsed = parse_text(text)
    save_parsed_input(db, "manual_text", text, parsed)
    return RedirectResponse("/", status_code=303)


@app.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    stored = _save_upload(file)
    suffix = stored.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        process_excel(db, stored)
    elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".webm"}:
        transcript = transcribe_audio(stored)
        parsed = parse_text(transcript)
        raw = save_parsed_input(db, "audio", transcript, parsed)
        db.add(models.UploadedFile(raw_input_id=raw.id, filename=file.filename or stored.name, stored_path=str(stored), content_type=file.content_type))
        db.commit()
    else:
        text = f"Archivo recibido: {file.filename}. Revisar manualmente."
        parsed = parse_text(text)
        raw = save_parsed_input(db, "document", text, parsed)
        db.add(models.UploadedFile(raw_input_id=raw.id, filename=file.filename or stored.name, stored_path=str(stored), content_type=file.content_type))
        db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/summary")
def create_summary(db: Session = Depends(get_db)):
    generate_daily_summary(db, today_local())
    return RedirectResponse("/", status_code=303)


@app.get("/command", response_class=HTMLResponse)
def command(request: Request, q: str = "", db: Session = Depends(get_db)):
    result = run_command(db, q)
    return templates.TemplateResponse("command.html", {"request": request, "query": q, "result": result})


def run_command(db: Session, command: str) -> str:
    command = command.strip()
    today = today_local()
    if command == "/pendientes":
        tasks = db.query(models.Task).filter(models.Task.status == "open").order_by(models.Task.due_date.asc()).all()
        return "\n".join(_task_line(task) for task in tasks) or "No hay pendientes abiertos."
    if command == "/hoy":
        tasks = db.query(models.Task).filter(models.Task.status == "open", models.Task.due_date == today).all()
        return "\n".join(_task_line(task) for task in tasks) or "No hay tareas para hoy."
    if command == "/semana":
        week_end = date.fromordinal(today.toordinal() + 7)
        tasks = db.query(models.Task).filter(models.Task.status == "open", models.Task.due_date <= week_end).all()
        return "\n".join(_task_line(task) for task in tasks) or "No hay tareas fechadas esta semana."
    if command == "/pipeline":
        opps = db.query(models.Opportunity).order_by(models.Opportunity.created_at.desc()).all()
        return "\n".join(f"{opp.client_alias or 'Sin cliente'} | {opp.stage} | {opp.currency or ''} {opp.amount or ''}" for opp in opps) or "Pipeline vacío."
    if command == "/resumen":
        summary = generate_daily_summary(db, today)
        return summary.content
    if command == "/revisar ambiguos":
        items = db.query(models.UnresolvedEntity).filter(models.UnresolvedEntity.resolved.is_(False)).all()
        return "\n".join(f"#{item.id} {item.value}: {item.reason}" for item in items) or "No hay ambiguos pendientes."
    if command.startswith("/cliente "):
        term = command.replace("/cliente ", "", 1).strip()
        notes = search_clients(db, term)
        return "\n".join(f"{note.created_at:%Y-%m-%d} | {note.client_alias or 'Sin cliente'} | {note.summary}" for note in notes) or "No encontré notas para ese cliente."
    if command.startswith("/buscar "):
        term = command.replace("/buscar ", "", 1).strip()
        notes = search_clients(db, term)
        return "\n".join(f"{note.created_at:%Y-%m-%d} | {note.summary}" for note in notes) or "No encontré coincidencias."
    if command == "/whatsapp-test":
        try:
            assert_zero_cost_allowed("send_whatsapp")
        except CostBlockedError as exc:
            return str(exc)
        return "WhatsApp habilitado para test sin bloqueo de costo."
    return "Comando no reconocido. Probá /pendientes, /hoy, /semana, /pipeline, /resumen, /buscar texto o /revisar ambiguos."


def _save_upload(file: UploadFile) -> Path:
    safe_name = Path(file.filename or "upload.bin").name
    destination = settings.storage_dir / safe_name
    counter = 1
    while destination.exists():
        destination = settings.storage_dir / f"{destination.stem}-{counter}{destination.suffix}"
        counter += 1
    with destination.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    return destination


def _task_line(task: models.Task) -> str:
    due = task.due_date.isoformat() if task.due_date else "sin fecha"
    return f"#{task.id} {task.client_alias or 'Sin cliente'}: {task.description} ({due})"
