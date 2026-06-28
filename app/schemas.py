from pydantic import BaseModel, Field


class Person(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None


class CommercialContext(BaseModel):
    product_or_need: str | None = None
    stage: str = "unknown"
    amount: float | None = None
    currency: str | None = None
    probability: float | None = None


class ParsedTask(BaseModel):
    description: str
    owner: str = "Juan"
    due_date: str | None = None
    priority: str = "medium"
    status: str = "open"


class DetectedDate(BaseModel):
    date: str
    meaning: str = "other"


class ParsedMessage(BaseModel):
    message_type: str = "unknown"
    client_alias: str | None = None
    company_name: str | None = None
    people: list[Person] = Field(default_factory=list)
    summary: str
    commercial_context: CommercialContext = Field(default_factory=CommercialContext)
    tasks: list[ParsedTask] = Field(default_factory=list)
    dates_detected: list[DetectedDate] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    needs_review: bool = True
