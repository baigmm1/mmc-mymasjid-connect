"""Example database integration with FastAPI endpoints."""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import select

Base = declarative_base()


class User(Base):
    """User model for demonstration."""

    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    full_name = Column(String(255))
    is_active = Column(bool, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Example usage in FastAPI endpoints:
"""
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session

app = FastAPI()


@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    '''Get a user by ID.'''
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    return user


@app.post("/users")
async def create_user(
    email: str,
    full_name: str,
    session: AsyncSession = Depends(get_session),
):
    '''Create a new user.'''
    user = User(email=email, full_name=full_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    '''List all users with pagination.'''
    query = select(User).offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    full_name: str,
    is_active: bool,
    session: AsyncSession = Depends(get_session),
):
    '''Update a user.'''
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.full_name = full_name
    user.is_active = is_active
    await session.commit()
    await session.refresh(user)
    return user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    '''Delete a user.'''
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await session.delete(user)
    await session.commit()
    return {"message": "User deleted"}
"""
