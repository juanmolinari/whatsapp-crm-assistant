from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contacts: Mapped[list["Contact"]] = relationship(back_populates="company")
    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped[Company | None] = relationship(back_populates="contacts")


class RawInput(Base):
    __tablename__ = "raw_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(50))
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    notes: Mapped[list["ClientNote"]] = relationship(back_populates="raw_input")
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(back_populates="raw_input")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    raw_input: Mapped[RawInput | None] = relationship(back_populates="uploaded_files")


class ClientNote(Base):
    __tablename__ = "client_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    client_alias: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    original_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    raw_input: Mapped[RawInput | None] = relationship(back_populates="notes")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    client_alias: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(120), default="Juan")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    client_alias: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    product_or_need: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="unknown")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    company: Mapped[Company | None] = relationship(back_populates="opportunities")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    client_alias: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="manual")
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UnresolvedEntity(Base):
    __tablename__ = "unresolved_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_input_id: Mapped[int | None] = mapped_column(ForeignKey("raw_inputs.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
