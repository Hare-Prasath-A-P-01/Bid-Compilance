from typing import List
import datetime
import json

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.notifications import create_notification
from app.database import get_db

router = APIRouter(prefix="/api/tenders/{tender_id}/bids", tags=["bids"])


@router.post("", response_model=schemas.BidOut)
def create_bid(
    tender_id: int,
    payload: schemas.BidCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    if tender.status in {models.TenderStatus.closed.value, models.TenderStatus.awarded.value, models.TenderStatus.archived.value}:
        raise HTTPException(status_code=409, detail=f"Bids cannot be added to a {tender.status.lower()} tender")
    if tender.submission_deadline and tender.submission_deadline <= datetime.datetime.utcnow():
        raise HTTPException(status_code=409, detail="The tender submission deadline has passed")

    bid = models.Bid(tender_id=tender_id, bidder_name=payload.bidder_name, bidder_company=payload.bidder_company)
    db.add(bid)
    db.flush()

    db.add(models.AuditLog(bid_id=bid.id, user_id=current_user.id, action="BID_CREATED",
                            details=f"Bid registered for bidder {payload.bidder_name}"))
    db.commit()
    db.refresh(bid)
    return bid


@router.patch("/{bid_id}/status", response_model=schemas.BidOut)
def update_bid_status(
    tender_id: int,
    bid_id: int,
    payload: schemas.BidStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    transitions = {
        "Draft": {"Submitted", "Withdrawn"},
        "Submitted": {"Under review", "Withdrawn"},
        "Under review": {"Accepted", "Rejected", "Withdrawn"},
        "Accepted": set(),
        "Rejected": set(),
        "Withdrawn": {"Draft"},
    }
    if payload.status not in transitions.get(bid.submission_status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot move bid from {bid.submission_status} to {payload.status}")
    if payload.status in {"Accepted", "Rejected"} and current_user.role not in (models.UserRole.admin, models.UserRole.reviewer):
        raise HTTPException(status_code=403, detail="Only reviewers or admins can make the final bid decision")
    if payload.status == "Submitted" and not bid.documents:
        raise HTTPException(status_code=400, detail="Upload at least one document before submitting the bid")

    bid.submission_status = payload.status
    if payload.status == "Submitted":
        bid.submitted_version += 1
        snapshot = [
            {"filename": document.original_filename, "status": document.status.value, "requirement_id": document.requirement_id}
            for document in bid.documents
        ]
        db.add(models.BidVersion(
            bid_id=bid.id,
            version=bid.submitted_version,
            status=payload.status,
            document_snapshot=json.dumps(snapshot),
            created_by=current_user.id,
        ))
    db.add(models.AuditLog(
        bid_id=bid.id,
        user_id=current_user.id,
        action="BID_STATUS_CHANGED",
        details=f"Bid status changed to {payload.status}",
    ))
    for document in bid.documents:
        if document.assigned_reviewer_id and document.assigned_reviewer_id != current_user.id:
            create_notification(
                db,
                document.assigned_reviewer_id,
                "bid_status",
                "Bid status changed",
                f"Bid for {bid.bidder_name} is now {payload.status}.",
                f"/tenders/{tender_id}/bids/{bid_id}",
            )
    db.commit()
    db.refresh(bid)
    return bid


@router.get("/{bid_id}/versions", response_model=List[schemas.BidVersionOut])
def bid_versions(
    tender_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    return db.query(models.BidVersion).filter(models.BidVersion.bid_id == bid_id).order_by(models.BidVersion.version.desc()).all()


@router.get("", response_model=List[schemas.BidOut])
def list_bids(tender_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    return db.query(models.Bid).filter(models.Bid.tender_id == tender_id).all()


@router.get("/{bid_id}", response_model=schemas.BidOut)
def get_bid(tender_id: int, bid_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    return bid


@router.get("/{bid_id}/audit-log", response_model=List[schemas.AuditLogOut])
def bid_audit_log(tender_id: int, bid_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)
    return sorted(bid.audit_logs, key=lambda a: a.timestamp, reverse=True)


@router.get("/{bid_id}/export.csv")
def export_bid_csv(
    tender_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Bidder", "Company", "Compliance score", "Risk", "Document", "Status", "Review", "Evidence", "Notes"])
    for document in bid.documents:
        writer.writerow([
            bid.bidder_name,
            bid.bidder_company or "",
            bid.compliance_score or 0,
            bid.risk_level or "",
            document.original_filename,
            document.status.value if document.status else "",
            document.review_status,
            document.matched_keywords or "",
            document.review_comment or document.notes or "",
        ])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bid-{bid_id}-compliance.csv"'},
    )


@router.get("/{bid_id}/export.pdf")
def export_bid_pdf(
    tender_id: int,
    bid_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    from app.services.pdf_report import generate_compliance_pdf

    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    auth.ensure_tender_access(bid.tender, current_user)

    pdf_buffer = generate_compliance_pdf(bid, bid.tender)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bid-{bid_id}-compliance-certificate.pdf"'},
    )

