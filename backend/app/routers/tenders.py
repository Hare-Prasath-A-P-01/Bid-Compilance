import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.post("", response_model=schemas.TenderOut)
def create_tender(
    payload: schemas.TenderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if current_user.role != models.UserRole.admin and current_user.department and payload.department not in (None, current_user.department):
        raise HTTPException(status_code=403, detail="You can only create tenders for your department")
    existing = db.query(models.Tender).filter(models.Tender.reference_no == payload.reference_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="A tender with this reference number already exists")

    tender = models.Tender(
        reference_no=payload.reference_no,
        title=payload.title,
        department=payload.department,
        theme=payload.theme,
        description=payload.description,
        submission_deadline=payload.submission_deadline,
        created_by=current_user.id,
    )
    db.add(tender)
    db.flush()

    for req in payload.requirements:
        db.add(models.Requirement(
            tender_id=tender.id,
            name=req.name,
            keywords=req.keywords,
            aliases=req.aliases,
            mandatory=req.mandatory,
            critical=req.critical,
            weight=req.weight,
            description=req.description,
        ))

    db.commit()
    db.refresh(tender)
    return tender


@router.get("", response_model=List[schemas.TenderSummary])
def list_tenders(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    query = db.query(models.Tender)
    if current_user.role != models.UserRole.admin and current_user.department:
        query = query.filter(
            (models.Tender.department == current_user.department) | (models.Tender.department.is_(None))
        )
    tenders = query.all()
    result = []
    for t in tenders:
        result.append(schemas.TenderSummary(
            id=t.id, reference_no=t.reference_no, title=t.title,
            department=t.department, status=t.status, submission_deadline=t.submission_deadline,
            bid_count=len(t.bids),
        ))
    return result


@router.get("/{tender_id}", response_model=schemas.TenderOut)
def get_tender(tender_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    return tender


@router.patch("/{tender_id}", response_model=schemas.TenderOut)
def update_tender(
    tender_id: int,
    payload: schemas.TenderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    if tender.status != models.TenderStatus.draft.value:
        raise HTTPException(status_code=409, detail="Only draft tenders can be edited")
    if current_user.role != models.UserRole.admin and current_user.department and payload.department not in (None, current_user.department):
        raise HTTPException(status_code=403, detail="You can only assign tenders to your department")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tender, field, value)
    db.commit()
    db.refresh(tender)
    return tender


@router.patch("/{tender_id}/status", response_model=schemas.TenderOut)
def update_tender_status(
    tender_id: int,
    payload: schemas.TenderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    transitions = {
        "Draft": {"Published", "Archived"},
        "Published": {"Closed", "Archived"},
        "Closed": {"Awarded", "Archived"},
        "Awarded": {"Archived"},
        "Archived": set(),
    }
    if payload.status not in transitions.get(tender.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot move tender from {tender.status} to {payload.status}")
    if payload.status == "Published" and not tender.requirements:
        raise HTTPException(status_code=400, detail="Add at least one requirement before publishing")
    if payload.status == "Published" and tender.submission_deadline and tender.submission_deadline <= datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Submission deadline must be in the future")
    tender.status = payload.status
    db.add(models.AuditLog(action="TENDER_STATUS_CHANGED", details=f"Tender {tender.id}: {payload.status}"))
    db.commit()
    db.refresh(tender)
    return tender


@router.post("/{tender_id}/requirements", response_model=schemas.RequirementOut)
def add_requirement(
    tender_id: int,
    payload: schemas.RequirementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(models.UserRole.admin)),
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    auth.ensure_tender_access(tender, current_user)
    req = models.Requirement(tender_id=tender_id, **payload.model_dump())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req
