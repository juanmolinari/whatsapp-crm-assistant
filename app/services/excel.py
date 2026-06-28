from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.services.parser import parse_text
from app.services.repository import save_parsed_input

COLUMN_ALIASES = {
    "cliente": "client",
    "client": "client",
    "empresa": "company",
    "company": "company",
    "monto": "amount",
    "amount": "amount",
    "etapa": "stage",
    "stage": "stage",
    "fecha": "date",
    "date": "date",
    "comentario": "comment",
    "comentarios": "comment",
    "nota": "comment",
    "proximo paso": "next_step",
    "próximo paso": "next_step",
    "next step": "next_step",
    "follow up": "next_step",
}


def process_excel(db: Session, path: Path) -> int:
    frame = pd.read_excel(path)
    if frame.empty:
        return 0
    normalized = {_normalize_column(col): col for col in frame.columns}
    count = 0
    for _, row in frame.iterrows():
        text = _row_to_text(row, normalized)
        if not text.strip():
            continue
        parsed = parse_text(text)
        save_parsed_input(db, "excel", text, parsed)
        count += 1
    return count


def _normalize_column(value: object) -> str:
    raw = str(value).strip().lower().replace("_", " ")
    return COLUMN_ALIASES.get(raw, raw)


def _field(row, normalized: dict[str, object], name: str) -> str:
    original = normalized.get(name)
    if original is None:
        return ""
    value = row.get(original)
    return "" if pd.isna(value) else str(value)


def _row_to_text(row, normalized: dict[str, object]) -> str:
    parts = []
    client = _field(row, normalized, "client")
    company = _field(row, normalized, "company")
    amount = _field(row, normalized, "amount")
    stage = _field(row, normalized, "stage")
    date_value = _field(row, normalized, "date")
    comment = _field(row, normalized, "comment")
    next_step = _field(row, normalized, "next_step")
    if client:
        parts.append(f"Cliente {client}.")
    if company:
        parts.append(f"Empresa {company}.")
    if amount:
        parts.append(f"Monto {amount}.")
    if stage:
        parts.append(f"Etapa {stage}.")
    if date_value:
        parts.append(f"Fecha {date_value}.")
    if comment:
        parts.append(comment)
    if next_step:
        parts.append(f"Próximo paso: {next_step}.")
    return " ".join(parts)
