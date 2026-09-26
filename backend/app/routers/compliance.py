from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/api/tenders/{tender_id}/bids/{bid_id}/compliance", tags=["compliance"])


@router.get("", response_model=schemas.ComplianceReport)
def get_compliance_report(
    tender_id: int, bid_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    bid = db.query(models.Bid).filter(models.Bid.id == bid_id, models.Bid.tender_id == tender_id).first()
    if not tender or not bid:
        raise HTTPException(status_code=404, detail="Tender or bid not found")
    auth.ensure_tender_access(tender, current_user)

    requirements = tender.requirements
    matched_req_ids = {
        d.requirement_id for d in bid.documents
        if d.status == models.DocumentStatus.matched and d.requirement_id
    }
    mismatched_req_ids = {
        d.requirement_id for d in bid.documents
        if d.status == models.DocumentStatus.mismatched and d.requirement_id
    }

    matched = [r.name for r in requirements if r.id in matched_req_ids]
    mismatched = [r.name for r in requirements if r.id in mismatched_req_ids]
    missing = [r.name for r in requirements if r.id not in matched_req_ids and r.id not in mismatched_req_ids]

    return schemas.ComplianceReport(
        bid_id=bid.id,
        bidder_name=bid.bidder_name,
        tender_title=tender.title,
        compliance_score=bid.compliance_score or 0.0,
        risk_level=bid.risk_level or models.RiskLevel.high.value,
        submission_status=bid.submission_status,
        submitted_version=bid.submitted_version,
        matched=matched,
        mismatched=mismatched,
        missing=missing,
        details=bid.documents,
    )
