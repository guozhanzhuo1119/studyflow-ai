from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

#用户类
class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True)#用户ID，主键
    username = Column(String(50), unique=True, nullable=False, index=True)#用户名，唯一，不能为空，索引
    password_hash = Column(String(200), nullable=False)#密码哈希
    email = Column(String(100))#邮箱
    created_at = Column(DateTime, nullable=False)
