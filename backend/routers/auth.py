from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import base64
import json
import hmac
import hashlib
import bcrypt

from backend.database import get_db, User
from pydantic import BaseModel

router = APIRouter()

SECRET_KEY = "super_secret_termux_key_change_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 1 day


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    padding_len = 4 - (len(data) % 4)
    if padding_len != 4:
        data += '=' * padding_len
    return base64.urlsafe_b64decode(data)

def custom_jwt_encode(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signature = hmac.new(secret.encode('utf-8'), f"{encoded_header}.{encoded_payload}".encode('utf-8'), hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def custom_jwt_decode(token: str, secret: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    
    encoded_header, encoded_payload, encoded_signature = parts
    expected_sig = hmac.new(secret.encode('utf-8'), f"{encoded_header}.{encoded_payload}".encode('utf-8'), hashlib.sha256).digest()
    
    if not hmac.compare_digest(base64url_encode(expected_sig), encoded_signature):
        raise ValueError("Invalid signature")
        
    payload = json.loads(base64url_decode(encoded_payload).decode('utf-8'))
    
    if 'exp' in payload:
        if datetime.utcnow().timestamp() > payload['exp']:
            raise ValueError("Token expired")
            
    return payload

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
         expire = datetime.utcnow() + expires_delta
    else:
         expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = custom_jwt_encode(to_encode, SECRET_KEY)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = custom_jwt_decode(token, SECRET_KEY)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class ProfileUpdate(BaseModel):
    username: str | None = None
    password: str | None = None

@router.put("/profile")
async def update_profile(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.username:
        # Check if username already exists
        existing = db.query(User).filter(User.username == data.username).first()
        if existing and existing.id != current_user.id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
        current_user.username = data.username
    
    if data.password:
        salt = bcrypt.gensalt()
        current_user.hashed_password = bcrypt.hashpw(data.password.encode('utf-8'), salt).decode('utf-8')
    
    db.commit()
    return {"message": "Profile updated successfully"}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "cloudflare_token": current_user.cloudflare_token}

