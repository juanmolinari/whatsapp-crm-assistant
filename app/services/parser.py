import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.schemas import CommercialContext, DetectedDate, ParsedMessage, ParsedTask

TASK_KEYWORDS = [
    "recordame",
    "llamar",
    "mandar mail",
    "hacer seguimiento",
    "follow-up",
    "follow up",
    "volver a contactar",
    "volver a escribir",
    "revisar",
    "preparar propuesta",
]

STAGE_KEYWORDS = {
    "proposal": ["propuesta", "pricing", "cotización", "cotizacion"],
    "negotiation": ["negociación", "negociacion", "negociando"],
    "meeting_scheduled": ["reunión", "reunion", "junté", "junte", "meeting"],
    "contacted": ["contacté", "contacte", "escribí", "escribi", "llamé", "llame"],
    "closed_lost": ["quedó frío", "quedo frio", "no insistir", "perdido"],
    "closed_won": ["cerrado", "ganado", "aceptó", "acepto"],
}

PRODUCT_KEYWORDS = [
    "capital de trabajo",
    "cash management",
    "deuda de corto plazo",
    "financiamiento",
    "línea",
    "linea",
    "pricing",
]


def today_local() -> date:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.timezone)).date()


def parse_text(text: str, base_date: date | None = None) -> ParsedMessage:
    base = base_date or today_local()
    clean_text = " ".join(text.strip().split())
    lower = clean_text.lower()
    client_alias = _extract_client_alias(clean_text)
    company_name = _extract_company_name(clean_text, client_alias)
    dates = _extract_dates(lower, base)
    tasks = _extract_tasks(clean_text, lower, dates)
    amount, currency = _extract_amount(clean_text)
    product_or_need = _extract_product(lower)
    stage = _extract_stage(lower, tasks, amount)
    message_type = _message_type(tasks, amount, stage)
    missing = []
    risk_flags = []

    if not client_alias and not company_name:
        missing.append("cliente o empresa")
    if "frío" in lower or "frio" in lower or "no insistir" in lower:
        risk_flags.append("Cliente con baja temperatura comercial o pedido de no insistir")

    context = CommercialContext(
        product_or_need=product_or_need,
        stage=stage,
        amount=amount,
        currency=currency,
        probability=_default_probability(stage),
    )
    return ParsedMessage(
        message_type=message_type,
        client_alias=client_alias,
        company_name=company_name,
        summary=_summarize(clean_text),
        commercial_context=context,
        tasks=tasks,
        dates_detected=dates,
        risk_flags=risk_flags,
        missing_information=missing,
        needs_review=bool(missing),
    )


def _extract_client_alias(text: str) -> str | None:
    patterns = [
        r"\b(?:cliente|clienta)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]*(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.-]*){0,2})",
        r"\bcon\s+(Cliente\s+[A-ZÁÉÍÓÚÑ0-9][\wÁÉÍÓÚÑáéíóúñ.-]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _trim_entity(match.group(1)).strip(" .,:;")
    return None


def _extract_company_name(text: str, client_alias: str | None) -> str | None:
    patterns = [
        r"\b(?:empresa|compañía|compania)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][\wÁÉÍÓÚÑáéíóúñ&.-]*(?:\s+[\wÁÉÍÓÚÑáéíóúñ&.-]+){0,3})",
        r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.-]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&.-]+){0,3})\s+(?:pidi[oó]|quiere|pidieron)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _trim_entity(match.group(1)).strip(" .,:;")
            if value and value != client_alias:
                return value
    return None


def _trim_entity(value: str) -> str:
    stop_words = [
        " el ",
        " la ",
        " los ",
        " las ",
        " para ",
        " por ",
        " pidio ",
        " pidió ",
        " pidi ",
        " quiere ",
        " quieren ",
    ]
    padded = f" {value.strip()} "
    lower = padded.lower()
    cut = len(padded)
    for stop in stop_words:
        idx = lower.find(stop)
        if idx >= 0:
            cut = min(cut, idx)
    return padded[:cut].strip()


def _extract_dates(lower: str, base: date) -> list[DetectedDate]:
    dates: list[DetectedDate] = []
    relative = {
        "hoy": base,
        "mañana": base + timedelta(days=1),
        "manana": base + timedelta(days=1),
        "pasado mañana": base + timedelta(days=2),
        "pasado manana": base + timedelta(days=2),
    }
    for word, resolved in relative.items():
        if word in lower:
            dates.append(DetectedDate(date=resolved.isoformat(), meaning=_date_meaning(lower)))

    weekdays = {
        "lunes": 0,
        "martes": 1,
        "miércoles": 2,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sábado": 5,
        "sabado": 5,
        "domingo": 6,
    }
    for word, idx in weekdays.items():
        if re.search(rf"\b{word}\b", lower):
            delta = (idx - base.weekday()) % 7
            delta = 7 if delta == 0 else delta
            dates.append(DetectedDate(date=(base + timedelta(days=delta)).isoformat(), meaning=_date_meaning(lower)))
    return _unique_dates(dates)


def _unique_dates(dates: list[DetectedDate]) -> list[DetectedDate]:
    seen = set()
    unique = []
    for item in dates:
        key = (item.date, item.meaning)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _date_meaning(lower: str) -> str:
    if "reunión" in lower or "reunion" in lower or "junt" in lower:
        return "meeting"
    if "venc" in lower or "deadline" in lower:
        return "deadline"
    if "follow" in lower or "seguimiento" in lower or "volver" in lower or "llamar" in lower:
        return "follow_up"
    return "other"


def _extract_tasks(text: str, lower: str, dates: list[DetectedDate]) -> list[ParsedTask]:
    if not any(keyword in lower for keyword in TASK_KEYWORDS):
        return []
    due = dates[0].date if dates else None
    priority = "high" if any(word in lower for word in ["urgente", "hoy", "vencido"]) else "medium"
    description = text
    for marker in ["recordame", "Recordame"]:
        description = description.replace(marker, "").strip()
    return [ParsedTask(description=description[:500], due_date=due, priority=priority)]


def _extract_amount(text: str) -> tuple[float | None, str | None]:
    match = re.search(r"\b(USD|US\$|ARS|EUR|\$)\s?([0-9]+(?:[.,][0-9]+)?)(k|m|mm)?\b", text, flags=re.IGNORECASE)
    if not match:
        return None, None
    currency_raw, value_raw, suffix = match.groups()
    value = float(value_raw.replace(",", "."))
    if suffix:
        suffix = suffix.lower()
        if suffix == "k":
            value *= 1_000
        elif suffix in {"m", "mm"}:
            value *= 1_000_000
    currency = "USD" if currency_raw.upper() in {"USD", "US$"} else currency_raw.upper()
    return value, currency


def _extract_stage(lower: str, tasks: list[ParsedTask], amount: float | None) -> str:
    for stage, keywords in STAGE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return stage
    if amount:
        return "proposal"
    if tasks:
        return "monitoring"
    return "unknown"


def _extract_product(lower: str) -> str | None:
    for keyword in PRODUCT_KEYWORDS:
        if keyword in lower:
            return keyword
    return None


def _message_type(tasks: list[ParsedTask], amount: float | None, stage: str) -> str:
    if tasks and stage == "monitoring":
        return "task"
    if amount or stage in {"proposal", "negotiation", "closed_won", "closed_lost"}:
        return "opportunity_update"
    if stage == "meeting_scheduled":
        return "meeting_note"
    if tasks:
        return "client_update"
    return "note"


def _default_probability(stage: str) -> float | None:
    return {
        "lead": 0.2,
        "contacted": 0.3,
        "meeting_scheduled": 0.4,
        "proposal": 0.55,
        "negotiation": 0.7,
        "closed_won": 1.0,
        "closed_lost": 0.0,
    }.get(stage)


def _summarize(text: str) -> str:
    return text if len(text) <= 280 else text[:277].rstrip() + "..."
