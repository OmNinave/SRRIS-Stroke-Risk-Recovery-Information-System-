from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.db import models, database
from app.core import security
from app.schemas import Token, DoctorResponse
from jose import JWTError, jwt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.Doctor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    doctor = db.query(models.Doctor).filter(models.Doctor.username == username).first()
    if doctor is None:
        raise credentials_exception
    return doctor

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    print(f"DEBUG: Login attempt - Username: '{form_data.username}', Password Length: {len(form_data.password)}")
    doctor = db.query(models.Doctor).filter(models.Doctor.username == form_data.username).first()
    
    if not doctor:
        print(f"DEBUG: Doctor '{form_data.username}' NOT found in database.")
        # Try case-insensitive search just in case
        doctor = db.query(models.Doctor).filter(models.Doctor.username.ilike(form_data.username)).first()
        if doctor:
            print(f"DEBUG: Found doctor '{doctor.username}' via case-insensitive search.")
    
    if doctor:
        is_valid = security.verify_password(form_data.password, doctor.hashed_password)
        print(f"DEBUG: Password verification for '{doctor.username}': {'SUCCESS' if is_valid else 'FAILED'}")
    
    if not doctor or not security.verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": doctor.username, "role": doctor.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=DoctorResponse)
def read_users_me(current_user: models.Doctor = Depends(get_current_user)):
    return current_user
