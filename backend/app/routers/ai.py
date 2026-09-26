from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, models, schemas
from app.database import get_db
from app.services import llm_service

router = APIRouter(prefix="/api/ai", tags=["ai-assist"])


class RequirementSuggestionRequest(BaseModel):
    tender_text: str


@router.post("/suggest-requirements", response_model=list[schemas.RequirementCreate])
def suggest_requirements(
    payload: RequirementSuggestionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return llm_service.suggest_requirements(payload.tender_text)