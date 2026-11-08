from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app import get_db
from app.models.user import User
from app.services.auth import hash_password, verify_password, create_access_token
from datetime import datetime
import uuid

router = APIRouter(prefix='/api/auth', tags=['认证'])


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


@router.post('/register', response_model=TokenResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    # 检查用户名是否存在
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(400, '用户名已存在')

    # 创建用户
    user = User(
        id=f'user-{uuid.uuid4().hex[:8]}',
        username=data.username,
        password_hash=hash_password(data.password),
        email=data.email,
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 生成 token
    token = create_access_token({"user_id": user.id, "username": user.username})

    return {
        'access_token': token,
        'token_type': 'bearer',
        'user_id': user.id,
        'username': user.username
    }


@router.post('/login', response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 查找用户
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(401, '用户名或密码错误')

    # 验证密码
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(401, '用户名或密码错误')

    # 生成 token
    token = create_access_token({"user_id": user.id, "username": user.username})

    return {
        'access_token': token,
        'token_type': 'bearer',
        'user_id': user.id,
        'username': user.username
    }


@router.get('/me')
def get_current_user(token: str, db: Session = Depends(get_db)):
    """获取当前用户信息"""
    from app.services.auth import decode_access_token

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(401, '无效的 token')

    user_id = payload.get('user_id')
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, '用户不存在')

    return {
        'user_id': user.id,
        'username': user.username,
        'email': user.email
    }
