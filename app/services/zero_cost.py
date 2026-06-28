from app.config import get_settings


class CostBlockedError(RuntimeError):
    pass


def assert_zero_cost_allowed(action: str) -> None:
    settings = get_settings()
    risky_actions = {"send_whatsapp", "external_llm", "external_transcription"}
    if settings.strict_zero_cost and action in risky_actions:
        raise CostBlockedError(
            f"Acción bloqueada por STRICT_ZERO_COST=true: {action}. "
            "El MVP no ejecuta acciones que puedan generar costos."
        )
