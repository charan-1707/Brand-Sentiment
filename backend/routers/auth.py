"""Authentication & Role Management (pipeline stage 1)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201,
             summary="Register a new Viewer account")
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(
        (models.User.username == data.username)
        | (models.User.email == data.email)).first()
    if exists:
        raise HTTPException(400, "Username or email already registered")
    user = models.User(username=data.username, email=data.email,
                       hashed_password=auth.hash_password(data.password),
                       role=models.ROLE_VIEWER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token, summary="Log in (form)")
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.username == form.username).first()
    if not user or not auth.verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")
    return schemas.Token(access_token=auth.create_access_token(user.username),
                         user=user)


@router.get("/me", response_model=schemas.UserOut, summary="Current user")
def me(user: models.User = Depends(auth.get_current_user)):
    return user


@router.get("/users", response_model=list[schemas.UserOut],
            summary="List users (admin)")
def list_users(_: models.User = Depends(auth.require_admin),
               db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.created_at).all()


@router.patch("/users/{user_id}/role", response_model=schemas.UserOut,
              summary="Change a user's role (admin)")
def set_role(user_id: int, data: schemas.UserRoleUpdate,
             admin: models.User = Depends(auth.require_admin),
             db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot change your own role")
    if data.role not in models.VALID_ROLES:
        raise HTTPException(400, "Invalid role")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/active", response_model=schemas.UserOut,
              summary="Activate/deactivate a user (admin)")
def set_active(user_id: int, data: schemas.UserActiveUpdate,
               admin: models.User = Depends(auth.require_admin),
               db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot deactivate yourself")
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user
