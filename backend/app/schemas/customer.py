from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class CustomerBase(BaseModel):
    companyName: str
    contactName: str
    pan: str
    cin: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    tags: List[str] = []
    status: str = "ACTIVE"
    risk: str = "LOW"

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    companyName: Optional[str] = None
    contactName: Optional[str] = None
    pan: Optional[str] = None
    cin: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    risk: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: str
    customId: str
    orgId: str
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True

class CustomerSummary(BaseModel):
    id: str
    customId: str
    companyName: str
    industry: Optional[str] = None
    status: str
    risk: str
    tags: List[str]
    documentCount: int = 0
    wcdlCount: int = 0
    lastActivity: Optional[datetime] = None
