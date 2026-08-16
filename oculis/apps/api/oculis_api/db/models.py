from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


JSONType = JSON().with_variant(JSONB, "postgresql")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submitted_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    verdict: Mapped[str | None] = mapped_column(String(32))
    signals: Mapped[dict | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    browser_data: Mapped[dict | None] = mapped_column(JSONType)
    screenshot_path: Mapped[str | None] = mapped_column(Text)
    screenshot_mime: Mapped[str | None] = mapped_column(String(64))

    findings: Mapped[list[Finding]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="Finding.id"
    )
    redirects: Mapped[list[Redirect]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="Redirect.hop"
    )
    network_requests: Mapped[list[NetworkRequest]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="NetworkRequest.id"
    )
    screenshots: Mapped[list[Screenshot]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="Screenshot.id"
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="findings")


class Redirect(Base):
    __tablename__ = "redirects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    hop: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)

    analysis: Mapped[Analysis] = relationship(back_populates="redirects")


class NetworkRequest(Base):
    __tablename__ = "network_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(32))
    blocked: Mapped[bool] = mapped_column(default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="network_requests")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)

    analysis: Mapped[Analysis] = relationship(back_populates="screenshots")
