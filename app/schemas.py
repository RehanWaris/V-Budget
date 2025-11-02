from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from .models import UserRole, UserStatus, VendorStatus, BudgetStatus, ApprovalStage


class Message(BaseModel):
    detail: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    designation: Optional[str] = None
    team: Optional[str] = None
    supervisor: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserResponse(UserBase):
    id: int
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class OTPRequest(BaseModel):
    email: EmailStr
    otp: str


class AdminOTPRequest(BaseModel):
    user_id: int
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VendorRateCreate(BaseModel):
    item_name: str
    description: Optional[str] = None
    unit: str
    rate: float
    min_quantity: Optional[float] = None
    setup_charges: Optional[float] = None
    notes: Optional[str] = None
    category_tag: Optional[str] = None


class VendorRateResponse(VendorRateCreate):
    id: int

    class Config:
        orm_mode = True


class VendorCreate(BaseModel):
    name: str
    category: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = None
    region: Optional[str] = None
    rate_cards: List[VendorRateCreate]


class VendorCreateRequest(BaseModel):
    vendor: VendorCreate
    otp: str


class VendorResponse(BaseModel):
    id: int
    name: str
    category: str
    status: VendorStatus
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[EmailStr]
    gst_number: Optional[str]
    region: Optional[str]
    created_at: datetime
    updated_at: datetime
    rate_cards: List[VendorRateResponse]

    class Config:
        orm_mode = True


class BudgetItemCreate(BaseModel):
    category: str
    item_name: str
    vendor_id: Optional[int] = None
    rate: float
    quantity: float
    unit: str
    days: float = 1
    gst_percentage: float = 0
    notes: Optional[str] = None
    is_override: bool = False


class BudgetCreate(BaseModel):
    client_name: str
    event_name: str
    event_type: Optional[str] = None
    event_location: Optional[str] = None
    event_dates: Optional[str] = None
    event_days: Optional[int] = None
    remarks: Optional[str] = None
    items: List[BudgetItemCreate]


class BudgetItemResponse(BudgetItemCreate):
    id: int
    subtotal: float
    total: float

    class Config:
        orm_mode = True


class BudgetResponse(BaseModel):
    id: int
    client_name: str
    event_name: str
    event_type: Optional[str]
    event_location: Optional[str]
    event_dates: Optional[str]
    event_days: Optional[int]
    remarks: Optional[str]
    status: BudgetStatus
    created_at: datetime
    updated_at: datetime
    items: List[BudgetItemResponse]

    class Config:
        orm_mode = True


class ApprovalAction(BaseModel):
    budget_id: int
    stage: ApprovalStage
    approve: bool
    comments: Optional[str] = None


class DashboardMetrics(BaseModel):
    pending_approvals: int
    active_budgets: int
    upcoming_events: int
    recent_vendor_updates: int
