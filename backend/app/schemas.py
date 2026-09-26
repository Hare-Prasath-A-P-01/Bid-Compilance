import datetime
import re
from typing import Optional, List, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_strength(password: str) -> str:
    """Enterprise password policy enforcement."""
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
        raise ValueError("Password must contain at least one special character (e.g. !@#$%^&*).")
    return password


# ---------- Auth ----------
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    department: Optional[str] = None

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    department: Optional[str]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserAdminCreate(UserCreate):
    role: Literal["procurement_officer", "reviewer", "admin"] = "procurement_officer"


class UserUpdate(BaseModel):
    role: Optional[Literal["procurement_officer", "reviewer", "admin"]]
    department: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)


class PasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_strength(v)



# ---------- Requirements ----------
class RequirementCreate(BaseModel):
    name: str
    keywords: str
    aliases: Optional[str] = None
    mandatory: bool = True
    critical: bool = False
    weight: float = Field(default=1.0, ge=0.1, le=10.0)
    description: Optional[str] = None


class RequirementOut(RequirementCreate):
    id: int

    class Config:
        from_attributes = True


# ---------- Tenders ----------
class TenderCreate(BaseModel):
    reference_no: str
    title: str
    department: Optional[str] = None
    theme: Optional[str] = None
    description: Optional[str] = None
    submission_deadline: Optional[datetime.datetime] = None
    requirements: List[RequirementCreate] = []


class TenderUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    theme: Optional[str] = None
    description: Optional[str] = None
    submission_deadline: Optional[datetime.datetime] = None


class TenderStatusUpdate(BaseModel):
    status: Literal["Draft", "Published", "Closed", "Awarded", "Archived"]


class TenderOut(BaseModel):
    id: int
    reference_no: str
    title: str
    department: Optional[str]
    theme: Optional[str]
    description: Optional[str]
    status: str
    submission_deadline: Optional[datetime.datetime]
    created_at: datetime.datetime
    requirements: List[RequirementOut] = []

    class Config:
        from_attributes = True


class TenderSummary(BaseModel):
    id: int
    reference_no: str
    title: str
    department: Optional[str]
    status: str
    submission_deadline: Optional[datetime.datetime]
    bid_count: int = 0

    class Config:
        from_attributes = True


# ---------- Bids ----------
class BidCreate(BaseModel):
    bidder_name: str
    bidder_company: Optional[str] = None


class BidStatusUpdate(BaseModel):
    status: Literal["Draft", "Submitted", "Under review", "Accepted", "Rejected", "Withdrawn"]


class BidVersionOut(BaseModel):
    id: int
    version: int
    status: str
    document_snapshot: str
    created_by: Optional[int]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class BidDocumentOut(BaseModel):
    id: int
    requirement_id: Optional[int]
    original_filename: str
    status: str
    match_confidence: float
    notes: Optional[str]
    matched_keywords: Optional[str]
    extraction_method: Optional[str]
    text_quality: Optional[float]
    expiry_date: Optional[datetime.datetime]
    review_status: str
    review_comment: Optional[str]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime.datetime]
    assigned_reviewer_id: Optional[int]
    review_due_at: Optional[datetime.datetime]
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


class BidOut(BaseModel):
    id: int
    tender_id: int
    bidder_name: str
    bidder_company: Optional[str]
    submitted_at: datetime.datetime
    submission_status: str
    submitted_version: int
    compliance_score: Optional[float]
    risk_level: Optional[str]
    last_evaluated_at: Optional[datetime.datetime]
    documents: List[BidDocumentOut] = []

    class Config:
        from_attributes = True


class ReviewDecision(BaseModel):
    decision: Literal["approved", "rejected", "pending"]
    comment: Optional[str] = Field(default=None, max_length=1000)


class ReviewAssignment(BaseModel):
    reviewer_id: int
    due_at: Optional[datetime.datetime] = None


class ComplianceReport(BaseModel):
    bid_id: int
    bidder_name: str
    tender_title: str
    compliance_score: float
    risk_level: str
    submission_status: str
    submitted_version: int
    matched: List[str]
    mismatched: List[str]
    missing: List[str]
    details: List[BidDocumentOut]


class AuditLogOut(BaseModel):
    id: int
    action: str
    details: Optional[str]
    timestamp: datetime.datetime

    class Config:
        from_attributes = True


class ReviewQueueItem(BaseModel):
    document_id: int
    bid_id: int
    tender_id: int
    tender_title: str
    bidder_name: str
    filename: str
    status: str
    review_status: str
    due_at: Optional[datetime.datetime]
    overdue: bool


class NotificationOut(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    link: Optional[str]
    read_at: Optional[datetime.datetime]
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    tender_count: int
    bid_count: int
    document_count: int
    high_risk_bids: int
    average_compliance_score: float
    published_tenders: int
    pending_reviews: int
    overdue_reviews: int
