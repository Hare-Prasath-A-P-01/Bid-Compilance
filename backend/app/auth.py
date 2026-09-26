import datetime
import time
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
MAX_FAILED_LOGINS = 5
_failed_logins: dict[str, list[float]] = {}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def check_login_allowed(email: str) -> None:
    now = time.time()
    recent = [stamp for stamp in _failed_logins.get(email.lower(), []) if now - stamp < FAILED_LOGIN_WINDOW_SECONDS]
    _failed_logins[email.lower()] = recent
    if len(recent) >= MAX_FAILED_LOGINS:
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")


def record_failed_login(email: str) -> None:
    _failed_logins.setdefault(email.lower(), []).append(time.time())


def clear_failed_logins(email: str) -> None:
    _failed_logins.pop(email.lower(), None)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: models.UserRole):
    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def ensure_tender_access(tender: models.Tender, current_user: models.User) -> None:
    if current_user.role == models.UserRole.admin:
        return
    if current_user.department and tender.department and current_user.department != tender.department:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this department")
