from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app import models


def generate_daily_summary(db: Session, summary_date: date) -> models.DailySummary:
    yesterday = summary_date - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, time.min)
    today_start = datetime.combine(summary_date, time.min)
    notes_yesterday = (
        db.query(models.ClientNote)
        .filter(models.ClientNote.created_at >= yesterday_start, models.ClientNote.created_at < today_start)
        .order_by(models.ClientNote.created_at.desc())
        .all()
    )
    new_tasks = (
        db.query(models.Task)
        .filter(models.Task.created_at >= yesterday_start, models.Task.created_at < today_start)
        .order_by(models.Task.created_at.desc())
        .all()
    )
    overdue = (
        db.query(models.Task)
        .filter(models.Task.status == "open", models.Task.due_date < summary_date)
        .order_by(models.Task.due_date.asc())
        .all()
    )
    today_tasks = (
        db.query(models.Task)
        .filter(models.Task.status == "open", models.Task.due_date == summary_date)
        .order_by(models.Task.priority.desc())
        .all()
    )
    opportunities = (
        db.query(models.Opportunity)
        .filter(models.Opportunity.stage.notin_(["closed_won", "closed_lost"]))
        .order_by(models.Opportunity.created_at.desc())
        .limit(20)
        .all()
    )
    unresolved = (
        db.query(models.UnresolvedEntity)
        .filter(models.UnresolvedEntity.resolved.is_(False))
        .order_by(models.UnresolvedEntity.created_at.desc())
        .limit(20)
        .all()
    )
    content = render_summary(summary_date, notes_yesterday, new_tasks, overdue, today_tasks, opportunities, unresolved)
    existing = db.query(models.DailySummary).filter(models.DailySummary.summary_date == summary_date).one_or_none()
    if existing:
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing
    item = models.DailySummary(summary_date=summary_date, content=content)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def render_summary(summary_date, notes, new_tasks, overdue, today_tasks, opportunities, unresolved) -> str:
    touched = sorted({note.client_alias for note in notes if note.client_alias})
    sections = [
        ("Resumen de ayer", [note.summary for note in notes]),
        ("Clientes tocados", touched),
        ("Tareas nuevas", [_task_line(task) for task in new_tasks]),
        ("Tareas vencidas", [_task_line(task) for task in overdue]),
        ("Follow-ups para hoy", [_task_line(task) for task in today_tasks]),
        ("Oportunidades abiertas", [_opportunity_line(opp) for opp in opportunities]),
        ("Riesgos o temas sin resolver", [f"{item.value}: {item.reason}" for item in unresolved]),
        ("Próximas acciones recomendadas", [_task_line(task) for task in overdue[:3] + today_tasks[:5]]),
    ]
    panorama = _portfolio_line(opportunities, today_tasks, overdue)

    lines = [f"Resumen diario - {summary_date.isoformat()}"]
    section_number = 1
    for title, items in sections:
        clean_items = _clean_items(items)
        if not clean_items:
            continue
        lines.extend(["", f"{section_number}. {title}", _bullets(clean_items)])
        section_number += 1
    if panorama:
        lines.extend(["", f"{section_number}. Panorama general de la cartera", f"- {panorama}"])
    if len(lines) == 1:
        lines.extend(["", "Sin actividad registrada para los campos del resumen."])
    return "\n".join(lines)


def _bullets(items) -> str:
    return "\n".join(f"- {item}" for item in _clean_items(items))


def _clean_items(items) -> list[str]:
    return [str(item) for item in items if str(item).strip()]


def _task_line(task: models.Task) -> str:
    prefix = f"{task.client_alias}: " if task.client_alias else ""
    details = []
    if task.due_date:
        details.append(task.due_date.isoformat())
    if task.priority:
        details.append(task.priority)
    suffix = f" ({', '.join(details)})" if details else ""
    return f"{prefix}{task.description}{suffix}"


def _opportunity_line(opp: models.Opportunity) -> str:
    client = opp.client_alias or (opp.company.name if opp.company else None)
    parts = []
    if opp.product_or_need:
        parts.append(opp.product_or_need)
    if opp.stage and opp.stage != "unknown":
        parts.append(opp.stage)
    if opp.amount:
        parts.append(f"{opp.currency or ''} {opp.amount:,.0f}".strip())
    if client and parts:
        return f"{client}: {' - '.join(parts)}"
    if client:
        return client
    return " - ".join(parts)


def _portfolio_line(opportunities, today_tasks, overdue) -> str:
    parts = []
    if opportunities:
        parts.append(f"{len(opportunities)} oportunidades abiertas")
    if today_tasks:
        parts.append(f"{len(today_tasks)} follow-ups para hoy")
    if overdue:
        parts.append(f"{len(overdue)} tareas vencidas")
    return ", ".join(parts)
