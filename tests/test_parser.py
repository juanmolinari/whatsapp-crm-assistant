from datetime import date

from app.services.parser import parse_text


def test_parser_creates_task_and_relative_date():
    parsed = parse_text("Recordame llamar a Cliente B el lunes para seguimiento de propuesta.", base_date=date(2026, 6, 28))

    assert parsed.client_alias == "B"
    assert parsed.tasks
    assert parsed.tasks[0].due_date == "2026-06-29"
    assert parsed.message_type in {"client_update", "opportunity_update"}


def test_parser_extracts_amount_and_opportunity():
    parsed = parse_text("Empresa industrial pidió pricing para línea de USD 500k. Follow-up el viernes.", base_date=date(2026, 6, 28))

    assert parsed.company_name == "industrial"
    assert parsed.commercial_context.amount == 500000
    assert parsed.commercial_context.currency == "USD"
    assert parsed.commercial_context.stage == "proposal"
    assert parsed.tasks


def test_parser_marks_missing_client_for_review():
    parsed = parse_text("Mandar mail mañana por cash management.", base_date=date(2026, 6, 28))

    assert parsed.needs_review is True
    assert "cliente o empresa" in parsed.missing_information
