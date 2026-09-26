import datetime
import enum

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Enum, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    procurement_officer = "procurement_officer"
    reviewer = "reviewer"
    admin = "admin"


class RiskLevel(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class DocumentStatus(str, enum.Enum):
    matched = "Matched"
    mismatched = "Mismatched"
    missing = "Missing"


class TenderStatus(str, enum.Enum):
    draft = "Draft"
    published = "Published"
    closed = "Closed"
    awarded = "Awarded"
    archived = "Archived"


class BidStatus(str, enum.Enum):
    draft = "Draft"
    submitted = "Submitted"
    under_review = "Under review"
    accepted = "Accepted"
    rejected = "Rejected"
    withdrawn = "Withdrawn"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    department = Column(String, nullable=True, index=True)
    role = Column(Enum(UserRole), default=UserRole.procurement_officer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    department = Column(String, nullable=True)
    theme = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String, default=TenderStatus.draft.value, nullable=False)
    submission_deadline = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    requirements = relationship("Requirement", back_populates="tender", cascade="all, delete-orphan")
    bids = relationship("Bid", back_populates="tender", cascade="all, delete-orphan")


class Requirement(Base):
    """A single required document / eligibility item for a tender."""
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    name = Column(String, nullable=False)          # e.g. "GST Registration Certificate"
    keywords = Column(String, nullable=False)       # comma separated keywords used for matching
    aliases = Column(String, nullable=True)         # optional synonyms / alternate phrases
    mandatory = Column(Boolean, default=True)
    critical = Column(Boolean, default=False)
    weight = Column(Float, default=1.0)
    description = Column(String, nullable=True)

    tender = relationship("Tender", back_populates="requirements")


class Bid(Base):
    __tablename__ = "bids"
    __table_args__ = (
        Index("ix_bids_tender_status", "tender_id", "submission_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    bidder_name = Column(String, nullable=False)
    bidder_company = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    submission_status = Column(String, default=BidStatus.draft.value, nullable=False)
    submitted_version = Column(Integer, default=0, nullable=False)

    compliance_score = Column(Float, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    last_evaluated_at = Column(DateTime, nullable=True)

    tender = relationship("Tender", back_populates="bids")
    documents = relationship("BidDocument", back_populates="bid", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="bid", cascade="all, delete-orphan")
    versions = relationship("BidVersion", back_populates="bid", cascade="all, delete-orphan")


class BidVersion(Base):
    __tablename__ = "bid_versions"

    id = Column(Integer, primary_key=True, index=True)
    bid_id = Column(Integer, ForeignKey("bids.id"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    document_snapshot = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bid = relationship("Bid", back_populates="versions")


class BidDocument(Base):
    __tablename__ = "bid_documents"
    __table_args__ = (
        Index("ix_bid_documents_bid_req", "bid_id", "requirement_id"),
        Index("ix_bid_documents_assigned_status", "assigned_reviewer_id", "review_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bid_id = Column(Integer, ForeignKey("bids.id"))
    requirement_id = Column(Integer, ForeignKey("requirements.id"), nullable=True)

    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_hash = Column(String, index=True, nullable=True)
    extracted_text = Column(Text, nullable=True)
    matched_keywords = Column(String, nullable=True)
    extraction_method = Column(String, nullable=True)
    text_quality = Column(Float, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    status = Column(Enum(DocumentStatus), default=DocumentStatus.missing)
    match_confidence = Column(Float, default=0.0)
    notes = Column(String, nullable=True)
    review_status = Column(String, default="pending", nullable=False)
    review_comment = Column(String, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    assigned_reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_due_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    bid = relationship("Bid", back_populates="documents")
    requirement = relationship("Requirement")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_bid_timestamp", "bid_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bid_id = Column(Integer, ForeignKey("bids.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    bid = relationship("Bid", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    link = Column(String, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

