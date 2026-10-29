from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import select
from .base import Base, BaseModel

#Base = declarative_base()


class CountryCodes(Base):
    """CountryCodes model representing country codes data."""

    __tablename__ = "CountryCodes"

    CountryCode = Column(String(3), primary_key=True, index=True)
    CountryName = Column(String(50), unique=True, index=True, nullable=False)    
    

class StateCodes(Base):
    """StateCodes model representing state codes data."""

    __tablename__ = "StateCodes"

    StateId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    CountryCode = Column(String(3), index=True, nullable=False)
    StateCode = Column(String(5), index=True, nullable=False)
    StateName = Column(String(50), unique=True, index=True, nullable=False)

class KeyValuePairs(BaseModel):
    """KeyValuePairs model for storing generic key-value data.
    
    This model provides a flexible way to store various key-value pairs that
    can be used for configuration settings, application preferences, or other
    purposes. The key field is indexed and unique to ensure fast lookups and
    prevent duplicates.
    
    Attributes:
        Id: Auto-incrementing primary key
        Key: Unique key/name for the pair (max 255 characters)
        Value: The value associated with the key (max 4000 characters)
        Description: Optional description of what this key-value pair represents
        CreatedAt: Timestamp when the record was created
        UpdatedAt: Timestamp when the record was last modified"""

    __tablename__ = "KeyValuePairs"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Type = Column(Integer, nullable=False)
    Key = Column(Integer, index=True, nullable=False)
    Value = Column(String(255), nullable=False)

    

class NameValuePair(Base):
    """NameValuePair model for storing configuration settings and key-value data.
    
    This model provides a flexible way to store application settings, user preferences,
    or any other name-value pair data. The name field is indexed and unique to ensure
    fast lookups and prevent duplicates.
    
    Attributes:
        Id: Auto-incrementing primary key
        Name: Unique key/name for the setting (max 255 characters)
        Value: The value associated with the name (max 4000 characters)
        Description: Optional description of what this setting represents
        CreatedAt: Timestamp when the record was created
        UpdatedAt: Timestamp when the record was last modified
        
    Example:
        >>> pair = NameValuePair(Name="theme", Value="dark", Description="UI theme setting")
        >>> pair = NameValuePair(Name="max_upload_size", Value="10485760", Description="Max file upload in bytes")
    """

    __tablename__ = "NameValuePairs"

    Id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Type = Column(Integer, nullable=False)
    Name = Column(String(255), unique=True, index=True, nullable=False)
    Value = Column(String(4000), nullable=True)
