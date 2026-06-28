import json
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models
from app.schemas import ParsedMessage


def get_or_create_company(db: Session, name: str | None) -> models.Company | None:
    if not name:
        return None
    company = db.query(models.Company).filter(models.Company.name == name).one_or_none()
    if company:
        return company
    company = models.Company(name=name)
    db.add(company)
    db.flush()
    return company


def save_parsed_input(db: Session, source_type: str, original_text: str, parsed: ParsedMessage) -> models.RawInput:
    company = get_or_create_company(db, parsed.company_name)
    raw = models.RawInput(
        source_type=source_type,
        original_text=original_text,
        parsed_json=parsed.model_dump_json(indent=2),
        needs_review=parsed.needs_review,
    )
    db.add(raw)
    db.flush()
    note = models.ClientNote(
        raw_input_id=raw.id,
        company_id=company.id if company else None,
        client_alias=parsed.client_alias,
        summary=parsed.summary,
        original_text=original_text,
    )
    db.add(note)
    db.add(
        models.Interaction(
            raw_input_id=raw.id,
            company_id=company.id if company else None,
            client_alias=parsed.client_alias,
            channel=source_type,
            summary=parsed.summary,
        )
    )
    for task in parsed.tasks:
        db.add(
            models.Task(
                raw_input_id=raw.id,
                company_id=company.id if company else None,
                client_alias=parsed.client_alias,
                description=task.description,
                owner=task.owner,
                due_date=date.fromisoformat(task.due_date) if task.due_date else None,
                priority=task.priority,
                status=task.status,
            )
        )
    context = parsed.commercial_context
    if any([context.product_or_need, context.amount, context.stage != "unknown"]):
        db.add(
            models.Opportunity(
                raw_input_id=raw.id,
                company_id=company.id if company else None,
                client_alias=parsed.client_alias,
                product_or_need=context.product_or_need,
                stage=context.stage,
                amount=context.amount,
                currency=context.currency,
                probability=context.probability,
            )
        )
    for missing in parsed.missing_information:
        db.add(
            models.UnresolvedEntity(
                raw_input_id=raw.id,
                entity_type="missing_information",
                value=missing,
                reason="No se pudo inferir con confianza desde el input original.",
            )
        )
    db.commit()
    db.refresh(raw)
    return raw


def parsed_payload(raw: models.RawInput) -> dict:
    if not raw.parsed_json:
        return {}
    return json.loads(raw.parsed_json)


def search_clients(db: Session, query: str):
    like = f"%{query}%"
    return (
        db.query(models.ClientNote)
        .filter(or_(models.ClientNote.client_alias.ilike(like), models.ClientNote.summary.ilike(like)))
        .order_by(models.ClientNote.created_at.desc())
        .limit(50)
        .all()
    )
