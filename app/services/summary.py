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
    touched = sorted({note.client_alias or "Sin cliente" for note in notes})
    lines = [
        f"Resumen diario - {summary_date.isoformat()}",
        "",
        "1. Resumen de ayer",
        _bullets([note.summary for note in notes], "Sin notas registradas ayer."),
        "2. Clientes tocados",
        _bullets(touched, "No hubo clientes identificados."),
        "3. Tareas nuevas",
        _bullets([_task_line(task) for task in new_tasks], "No se crearon tareas nuevas."),
        "4. Tareas vencidas",
        _bullets([_task_line(task) for task in overdue], "No hay tareas vencidas."),
        "5. Follow-ups para hoy",
        _bullets([_task_line(task) for task in today_tasks], "No hay follow-ups fechados para hoy."),
        "6. Oportunidades abiertas",
        _bullets([_opportunity_line(opp) for opp in opportunities], "No hay oportunidades abiertas cargadas."),
        "7. Riesgos o temas sin resolver",
        _bullets([f"{item.value}: {item.reason}" for item in unresolved], "No hay ambiguos pendientes."),
        "8. Próximas acciones recomendadas",
        _bullets([_task_line(task) for task in overdue[:3] + today_tasks[:5]], "Cargar nuevas notas comerciales o revisar pipeline."),
        "9. Panorama general de la cartera",
        f"- {len(opportunities)} oportunidades abiertas, {len(today_tasks)} follow-ups para hoy, {len(overdue)} tareas vencidas.",
    ]
    return "\n".join(lines)


def _bullets(items, empty: str) -> str:
    clean = [str(item) for item in items if str(item).strip()]
    if not clean:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in clean)


def _task_line(task: models.Task) -> str:
    due = task.due_date.isoformat() if task.due_date else "sin fecha"
    client = task.client_alias or "sin cliente"
    return f"{client}: {task.description} ({due}, {task.priority})"


def _opportunity_line(opp: models.Opportunity) -> str:
    amount = f"{opp.currency or ''} {opp.amount:,.0f}" if opp.amount else "monto s/d"
    client = opp.client_alias or (opp.company.name if opp.company else "sin cliente")
    return f"{client}: {opp.product_or_need or 'necesidad s/d'} - {opp.stage} - {amount}"
