from datetime import date

from sqlalchemy.orm import Session

from app import models
from app.services.parser import today_local
from app.services.repository import search_clients
from app.services.summary import generate_daily_summary
from app.services.zero_cost import CostBlockedError, assert_zero_cost_allowed


def run_command(db: Session, command: str) -> str:
    command = command.strip()
    today = today_local()
    if command == "/start":
        return (
            "Listo. Mandame notas comerciales, audios, Excels o comandos.\n"
            "Comandos: /pendientes, /hoy, /semana, /pipeline, /resumen, /buscar texto, /revisar_ambiguos."
        )
    if command == "/ayuda":
        return (
            "Podés mandarme texto libre, notas de voz, Excel o documentos.\n"
            "Comandos: /pendientes, /hoy, /semana, /pipeline, /resumen, /buscar texto, /revisar_ambiguos."
        )
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
    if command in {"/revisar ambiguos", "/revisar_ambiguos"}:
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
    return "Comando no reconocido. Probá /pendientes, /hoy, /semana, /pipeline, /resumen, /buscar texto o /revisar_ambiguos."


def _task_line(task: models.Task) -> str:
    due = task.due_date.isoformat() if task.due_date else "sin fecha"
    return f"#{task.id} {task.client_alias or 'Sin cliente'}: {task.description} ({due})"
