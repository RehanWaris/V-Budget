import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    Boolean,
    ForeignKey,
    Float,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    employee = "employee"
    approver = "approver"
    accounts = "accounts"
    admin = "admin"


class UserStatus(str, enum.Enum):
    pending_self_otp = "pending_self_otp"
    pending_admin_approval = "pending_admin_approval"
    active = "active"
    rejected = "rejected"


class OTPPurpose(str, enum.Enum):
    self_registration = "self_registration"
    admin_approval = "admin_approval"
    vendor_unlock = "vendor_unlock"


class ApprovalStage(str, enum.Enum):
    requester = "requester"
    approver = "approver"
    accounts = "accounts"
    finalized = "finalized"


class VendorStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    rejected = "rejected"


class BudgetStatus(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    approved = "approved"
    returned = "returned"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    team = Column(String, nullable=True)
    supervisor = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.employee, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.pending_self_otp, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    otps = relationship("OneTimePassword", back_populates="user")
    vendors = relationship("Vendor", back_populates="created_by_user")
    budgets = relationship("Budget", back_populates="owner")
    approvals = relationship("Approval", back_populates="approver")


class OneTimePassword(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    purpose = Column(Enum(OTPPurpose), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="otps")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    contact_person = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    region = Column(String, nullable=True)
    status = Column(Enum(VendorStatus), default=VendorStatus.draft, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_by_user = relationship("User", back_populates="vendors")
    rate_cards = relationship("VendorRate", back_populates="vendor", cascade="all, delete-orphan")
    documents = relationship("VendorDocument", back_populates="vendor", cascade="all, delete-orphan")
    history_entries = relationship("VendorHistory", back_populates="vendor", cascade="all, delete-orphan")


class VendorRate(Base):
    __tablename__ = "vendor_rates"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    min_quantity = Column(Float, nullable=True)
    setup_charges = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    category_tag = Column(String, nullable=True)

    vendor = relationship("Vendor", back_populates="rate_cards")


class VendorDocument(Base):
    __tablename__ = "vendor_documents"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="documents")


class VendorHistory(Base):
    __tablename__ = "vendor_history"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    vendor = relationship("Vendor", back_populates="history_entries")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True)
    client_name = Column(String, nullable=False)
    event_name = Column(String, nullable=False)
    event_type = Column(String, nullable=True)
    event_location = Column(String, nullable=True)
    event_dates = Column(String, nullable=True)
    event_days = Column(Integer, nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(Enum(BudgetStatus), default=BudgetStatus.draft, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    owner = relationship("User", back_populates="budgets")
    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")
    documents = relationship("BudgetDocument", back_populates="budget", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="budget", cascade="all, delete-orphan")
    history_entries = relationship("BudgetHistory", back_populates="budget", cascade="all, delete-orphan")


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    rate = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    days = Column(Float, default=1, nullable=False)
    gst_percentage = Column(Float, default=0.0, nullable=False)
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    is_override = Column(Boolean, default=False, nullable=False)

    budget = relationship("Budget", back_populates="items")
    vendor = relationship("Vendor")


class BudgetDocument(Base):
    __tablename__ = "budget_documents"

    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    budget = relationship("Budget", back_populates="documents")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Enum(ApprovalStage), nullable=False)
    status = Column(String, nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    comments = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)

    budget = relationship("Budget", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class BudgetHistory(Base):
    __tablename__ = "budget_history"

    id = Column(Integer, primary_key=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    budget = relationship("Budget", back_populates="history_entries")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True)
    entity = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    details = Column(Text, nullable=True)

