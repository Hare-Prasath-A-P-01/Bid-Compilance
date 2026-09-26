import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/queue", response_model=list[schemas.ReviewQueueItem])
def review_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(models.UserRole.admin, models.UserRole.reviewer)),
):
    query = (
        db.query(models.BidDocument, models.Bid, models.Tender)
        .join(models.Bid, models.BidDocument.bid_id == models.Bid.id)
        .join(models.Tender, models.Bid.tender_id == models.Tender.id)
        .filter(models.BidDocument.review_status == "pending")
    )
    if current_user.role == models.UserRole.reviewer:
        query = query.filter(models.BidDocument.assigned_reviewer_id == current_user.id)
    if current_user.department:
        query = query.filter(
            (models.Tender.department == current_user.department) | (models.Tender.department.is_(None))
        )

    now = datetime.datetime.utcnow()
    result = []
    for document, bid, tender in query.order_by(models.BidDocument.review_due_at.asc()).all():
        result.append(schemas.ReviewQueueItem(
            document_id=document.id,
            bid_id=bid.id,
            tender_id=tender.id,
            tender_title=tender.title,
            bidder_name=bid.bidder_name,
            filename=document.original_filename,
            status=document.status.value,
            review_status=document.review_status,
            due_at=document.review_due_at,
            overdue=bool(document.review_due_at and document.review_due_at < now),
        ))
    return result