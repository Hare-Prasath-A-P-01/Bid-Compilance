import csv
import datetime
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=schemas.DashboardMetrics)
def dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender_query = db.query(models.Tender)
    if current_user.role != models.UserRole.admin and current_user.department:
        tender_query = tender_query.filter(
            (models.Tender.department == current_user.department) | (models.Tender.department.is_(None))
        )
    tender_ids = [tender_id for (tender_id,) in tender_query.with_entities(models.Tender.id).all()]
    bid_query = db.query(models.Bid).filter(models.Bid.tender_id.in_(tender_ids))
    scores = [score for (score,) in bid_query.with_entities(models.Bid.compliance_score).filter(models.Bid.compliance_score.isnot(None)).all()]
    return schemas.DashboardMetrics(
        tender_count=len(tender_ids),
        bid_count=bid_query.count(),
        document_count=db.query(models.BidDocument).join(models.Bid).filter(models.Bid.tender_id.in_(tender_ids)).count(),
        high_risk_bids=bid_query.filter(models.Bid.risk_level == models.RiskLevel.high).count(),
        average_compliance_score=round(sum(scores) / len(scores), 1) if scores else 0.0,
        published_tenders=tender_query.filter(models.Tender.status == models.TenderStatus.published.value).count(),
        pending_reviews=db.query(models.BidDocument).join(models.Bid).filter(
            models.Bid.tender_id.in_(tender_ids), models.BidDocument.review_status == "pending"
        ).count(),
        overdue_reviews=db.query(models.BidDocument).join(models.Bid).filter(
            models.Bid.tender_id.in_(tender_ids),
            models.BidDocument.review_status == "pending",
            models.BidDocument.review_due_at.isnot(None),
            models.BidDocument.review_due_at < datetime.datetime.utcnow(),
        ).count(),
    )


@router.get("/report.csv")
def export_portfolio_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender_query = db.query(models.Tender)
    if current_user.role != models.UserRole.admin and current_user.department:
        tender_query = tender_query.filter(
            (models.Tender.department == current_user.department) | (models.Tender.department.is_(None))
        )
    tender_ids = [tender_id for (tender_id,) in tender_query.with_entities(models.Tender.id).all()]
    bids = db.query(models.Bid).join(models.Tender).filter(models.Bid.tender_id.in_(tender_ids)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Tender", "Reference", "Bidder", "Company", "Bid status", "Score", "Risk", "Documents", "Pending reviews"])
    for bid in bids:
        pending = sum(1 for document in bid.documents if document.review_status == "pending")
        writer.writerow([
            bid.tender.title,
            bid.tender.reference_no,
            bid.bidder_name,
            bid.bidder_company or "",
            bid.submission_status,
            bid.compliance_score if bid.compliance_score is not None else "",
            bid.risk_level.value if bid.risk_level else "",
            len(bid.documents),
            pending,
        ])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bid-compliance-portfolio.csv"},
    )