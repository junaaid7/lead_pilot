import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def pk_uuid():
    # Python side par uuid4, aur database side par bhi default (raw SQL insert ke liye)
    return mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )


def created_at_col():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------- Market catalog


class CountryNiche(Base):
    __tablename__ = "country_niches"

    country: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    niche: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )


class City(Base):
    __tablename__ = "cities"

    geoname_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    country: Mapped[str] = mapped_column(CHAR(2))
    admin1: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    lat: Mapped[Decimal | None] = mapped_column(Numeric)
    lng: Mapped[Decimal | None] = mapped_column(Numeric)
    population: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_cities_country_name", "country", "name"),)


# ---------------------------------------------------------------- Discovery


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = pk_uuid()
    canonical_domain: Mapped[str | None] = mapped_column(Text)
    place_id: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(CHAR(2))
    city: Mapped[str | None] = mapped_column(Text)
    niche: Mapped[str] = mapped_column(Text)
    phone_e164: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = created_at_col()

    __table_args__ = (
        UniqueConstraint("canonical_domain", name="uq_businesses_canonical_domain"),
        UniqueConstraint("place_id", name="uq_businesses_place_id"),
        Index("ix_businesses_country_niche", "country", "niche"),
        Index("ix_businesses_phone_e164", "phone_e164"),
    )


# ---------------------------------------------------------------- Inspection


class Inspection(Base):
    """Immutable: naya check = nayi row, purani row kabhi edit nahi hoti."""

    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = pk_uuid()
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"))
    inspector_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # OK | BLOCKED | TIMEOUT | NO_WEBSITE
    has_website: Mapped[bool | None] = mapped_column(Boolean)
    wa_number_e164: Mapped[str | None] = mapped_column(Text)
    wa_status: Mapped[str | None] = mapped_column(Text)
    wa_type: Mapped[str | None] = mapped_column(Text)
    wa_type_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    wa_source_url: Mapped[str | None] = mapped_column(Text)
    chatbot_value: Mapped[str | None] = mapped_column(Text)
    chatbot_vendor: Mapped[str | None] = mapped_column(Text)
    chatbot_kind: Mapped[str | None] = mapped_column(Text)
    signals: Mapped[dict | None] = mapped_column(JSONB)
    evidence_uri: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = created_at_col()


Index(
    "ix_inspections_business_checked",
    Inspection.business_id,
    Inspection.checked_at.desc(),
)


# ---------------------------------------------------------------- Lead Search


class SearchJob(Base):
    __tablename__ = "search_jobs"

    id: Mapped[uuid.UUID] = pk_uuid()
    # users table Din 6 par banegi, tab yahan foreign key lagayenge
    user_id: Mapped[uuid.UUID] = mapped_column()
    country: Mapped[str] = mapped_column(CHAR(2))
    niche: Mapped[str] = mapped_column(Text)
    city_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    lead_count: Mapped[int] = mapped_column(Integer)
    filters: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    accepted_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    candidates_seen: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )
    shortfall: Mapped[dict | None] = mapped_column(JSONB)
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = created_at_col()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "lead_count BETWEEN 1 AND 200", name="ck_search_jobs_lead_count_range"
        ),
        CheckConstraint(
            "accepted_count <= lead_count", name="ck_search_jobs_accepted_lte_requested"
        ),
        Index("ix_search_jobs_user_created", "user_id", "created_at"),
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = pk_uuid()
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("search_jobs.id"))
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"))
    inspection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inspections.id"))
    hot_lead: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    feedback: Mapped[str | None] = mapped_column(Text)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()

    __table_args__ = (
        UniqueConstraint("job_id", "business_id", name="uq_leads_job_business"),
        Index("ix_leads_job_id", "job_id"),
    )


# ---------------------------------------------------------------- Usage / limits


class UsageLedger(Base):
    """Append-only. RESERVE = positive amount, RELEASE = negative amount.
    Aaj ka usage = aaj ki date ki rows ka SUM(amount)."""

    __tablename__ = "usage_ledger"

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = mapped_column()
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("search_jobs.id"))
    kind: Mapped[str] = mapped_column(Text)  # RESERVE | RELEASE
    amount: Mapped[int] = mapped_column(Integer)
    usage_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    created_at: Mapped[datetime] = created_at_col()

    __table_args__ = (Index("ix_usage_ledger_user_date", "user_id", "usage_date"),)


# ---------------------------------------------------------------- Export


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = mapped_column()
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("search_jobs.id"))
    format: Mapped[str] = mapped_column(Text)  # csv | xlsx
    row_count: Mapped[int] = mapped_column(Integer)
    file_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()

    __table_args__ = (Index("ix_exports_user_created", "user_id", "created_at"),)


class ExportItem(Base):
    __tablename__ = "export_items"

    id: Mapped[uuid.UUID] = pk_uuid()
    export_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exports.id"))
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"))

    __table_args__ = (
        UniqueConstraint("export_id", "lead_id", name="uq_export_items_export_lead"),
        # "Exclude leads I already exported" filter isi index se tez chalega
        Index("ix_export_items_lead_id", "lead_id"),
    )


# ---------------------------------------------------------------- Notifications / audit


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = pk_uuid()
    user_id: Mapped[uuid.UUID] = mapped_column()
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("search_jobs.id"))
    type: Mapped[str] = mapped_column(Text)  # JOB_COMPLETED | JOB_PARTIAL | ...
    title: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    email_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = created_at_col()

    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = pk_uuid()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(Text)  # e.g. USER_DELETED, LIMIT_CHANGED
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_col()

    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_actor", "actor_user_id"),
    )