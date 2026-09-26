import datetime
import hashlib
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.notifications import create_notification
from app.config import settings
from app.database import get_db
from app.services import document_processor, compliance_engine, llm_service

router = APIRouter(prefix="/api/tenders/{tender_id}/bids/{bid_id}/documents", tags=["documents"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}


def validate_magic_bytes(contents: bytes, ext: str) -> tuple[bool, str]:
    """Verify that file contents match the expected file signature/magic bytes."""
    if ext == ".pdf":
        if not contents.startswith(b"%PDF-"):
            return False, "Invalid PDF: File does not match the standard %PDF- header signature."
    elif ext == ".png":
        if not contents.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG image: File does not match the PNG binary signature."
    elif ext in {".jpg", ".jpeg"}:
        if not contents.startswith(b"\xff\xd8\xff"):
            return False, "Invalid JPEG image: File does not match the JPEG binary signature."
    elif ext == ".txt":
        # Text files shouldn't have binary null bytes and must decode cleanly
        if b"\x00" in contents[:1024]:
            return False, "Invalid text file: File contains binary null bytes, indicating a disguised executable or binary file."
        try:
            contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                contents.decode("latin-1")
            except Exception:
                return False, "Invalid text file: File cannot be decoded as standard text."
    return True, ""


@router.post("", response_model=schemas.BidDocumentOut)
def upload_document(
    tender_id: int,
    bid_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    if bid.submission_status != models.BidStatus.draft.value:
        raise HTTPException(status_code=409, detail="Documents can only be changed while the bid is in Draft")

    requirements = db.query(models.Requirement).filter(models.Requirement.tender_id == tender_id).all()

    filename = os.path.basename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, PNG, JPG, JPEG, or TXT.")

    contents = file.file.read(MAX_UPLOAD_SIZE + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File is too large. Maximum upload size is 10 MB.")

    is_valid, reason = validate_magic_bytes(contents, ext)
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)


    content_hash = hashlib.sha256(contents).hexdigest()
    duplicate = db.query(models.BidDocument).filter(
        models.BidDocument.bid_id == bid_id,
        models.BidDocument.content_hash == content_hash,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This document has already been uploaded for this bid.")

    # store the file
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(contents)

    # extract + classify
    text, extraction_method, text_quality = document_processor.extract_document(stored_path)
    matched_req, confidence = compliance_engine.classify_document(text, requirements)
    issues = compliance_engine.detect_issues(text, text_quality) if matched_req else []
    evidence = compliance_engine.matching_keywords(text, matched_req) if matched_req else []
    expiry_date = compliance_engine.extract_expiry_date(text)

    status_val = models.DocumentStatus.missing
    notes = None
    if matched_req and not issues:
        status_val = models.DocumentStatus.matched
        notes = f"Matched '{matched_req.name}' (confidence {confidence})"
    elif matched_req and issues:
        status_val = models.DocumentStatus.mismatched
        notes = llm_service.explain_match(matched_req.name, text, issues)
    else:
        status_val = models.DocumentStatus.mismatched
        notes = "Could not confidently match this document to any requirement — needs manual review"

    doc = models.BidDocument(
        bid_id=bid_id,
        requirement_id=matched_req.id if matched_req else None,
        original_filename=filename,
        stored_path=stored_path,
        content_hash=content_hash,
        extracted_text=text,
        matched_keywords=", ".join(evidence) or None,
        extraction_method=extraction_method,
        text_quality=text_quality,
        expiry_date=expiry_date,
        status=status_val,
        match_confidence=confidence,
        notes=notes,
    )
    db.add(doc)
    db.add(models.AuditLog(
        bid_id=bid_id, user_id=current_user.id, action="DOCUMENT_UPLOADED",
        details=f"Uploaded '{filename}' -> {status_val.value}",
    ))
    db.flush()

    # recompute rollup score
    score, risk = compliance_engine.evaluate_bid(bid, requirements)
    bid.compliance_score = score
    bid.risk_level = risk
    bid.last_evaluated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{document_id}/review", response_model=schemas.BidDocumentOut)
def review_document(
    tender_id: int, bid_id: int, document_id: int,
    payload: schemas.ReviewDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    doc = db.query(models.BidDocument).filter(
        models.BidDocument.id == document_id, models.BidDocument.bid_id == bid_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    if (
        current_user.role != models.UserRole.admin
        and doc.assigned_reviewer_id
        and doc.assigned_reviewer_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="This document is assigned to another reviewer")

    if payload.decision == "approved":
        doc.status = models.DocumentStatus.matched
    elif payload.decision == "rejected":
        doc.status = models.DocumentStatus.mismatched
    doc.review_status = payload.decision
    doc.review_comment = payload.comment
    doc.reviewed_by = current_user.id
    doc.reviewed_at = datetime.datetime.utcnow()

    requirements = db.query(models.Requirement).filter(models.Requirement.tender_id == tender_id).all()
    score, risk = compliance_engine.evaluate_bid(bid, requirements)
    bid.compliance_score = score
    bid.risk_level = risk
    bid.last_evaluated_at = datetime.datetime.utcnow()
    db.add(models.AuditLog(
        bid_id=bid_id, user_id=current_user.id, action="DOCUMENT_REVIEWED",
        details=f"{payload.decision.title()} review for '{doc.original_filename}'",
    ))
    if doc.assigned_reviewer_id and doc.assigned_reviewer_id != current_user.id:
        create_notification(
            db,
            doc.assigned_reviewer_id,
            "review_update",
            "Document review updated",
            f"'{doc.original_filename}' was marked {payload.decision}.",
            f"/tenders/{tender_id}/bids/{bid_id}",
        )
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{document_id}/assignment", response_model=schemas.BidDocumentOut)
def assign_document(
    tender_id: int, bid_id: int, document_id: int,
    payload: schemas.ReviewAssignment,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(models.UserRole.admin, models.UserRole.reviewer)),
):
    doc = db.query(models.BidDocument).filter(
        models.BidDocument.id == document_id, models.BidDocument.bid_id == bid_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    reviewer = db.query(models.User).filter(models.User.id == payload.reviewer_id).first()
    if not reviewer or reviewer.role not in (models.UserRole.reviewer, models.UserRole.admin):
        raise HTTPException(status_code=400, detail="Assigned user must be a reviewer or admin")
    if reviewer.department and bid.tender.department and reviewer.department != bid.tender.department:
        raise HTTPException(status_code=400, detail="Reviewer must belong to the tender department")

    doc.assigned_reviewer_id = reviewer.id
    doc.review_due_at = payload.due_at
    db.add(models.AuditLog(
        bid_id=bid_id,
        user_id=current_user.id,
        action="DOCUMENT_ASSIGNED",
        details=f"Assigned '{doc.original_filename}' to {reviewer.email}",
    ))
    create_notification(
        db,
        reviewer.id,
        "review_assignment",
        "New document assigned",
        f"Review '{doc.original_filename}' for {bid.bidder_name}.",
        f"/tenders/{tender_id}/bids/{bid_id}",
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{document_id}")
def delete_document(
    tender_id: int, bid_id: int, document_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    doc = db.query(models.BidDocument).filter(
        models.BidDocument.id == document_id, models.BidDocument.bid_id == bid_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    bid = db.query(models.Bid).filter(models.Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    if bid.submission_status != models.BidStatus.draft.value:
        raise HTTPException(status_code=409, detail="Documents can only be changed while the bid is in Draft")
    requirements = db.query(models.Requirement).filter(models.Requirement.tender_id == tender_id).all()

    if doc.stored_path and os.path.exists(doc.stored_path):
        os.remove(doc.stored_path)
    db.delete(doc)
    db.flush()

    score, risk = compliance_engine.evaluate_bid(bid, requirements)
    bid.compliance_score = score
    bid.risk_level = risk
    bid.last_evaluated_at = datetime.datetime.utcnow()

    db.commit()
    return {"detail": "Document removed"}
