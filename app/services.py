from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .models import (
    ActivityLog,
    Approval,
    ApprovalStage,
    Budget,
    BudgetDocument,
    BudgetHistory,
    BudgetItem,
    BudgetStatus,
    OneTimePassword,
    OTPPurpose,
    User,
    UserRole,
    UserStatus,
    Vendor,
    VendorHistory,
    VendorRate,
    VendorStatus,
)
from .schemas import BudgetCreate, BudgetResponse, VendorCreate
from .security import get_password_hash
from .utils import generate_otp, log_admin_notification, otp_expiry, save_upload


ADMIN_DEFAULT_PASSWORD = "Admin@123"


def seed_admin(db: Session, admin_email: str) -> None:
    if db.query(User).filter(User.email == admin_email).first():
        return
    admin = User(
        name="System Admin",
        email=admin_email,
        hashed_password=get_password_hash(ADMIN_DEFAULT_PASSWORD),
        role=UserRole.admin,
        status=UserStatus.active,
    )
    db.add(admin)
    db.commit()


def register_user(db: Session, payload: dict) -> User:
    if db.query(User).filter(User.email == payload["email"]).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        name=payload["name"],
        email=payload["email"],
        phone=payload.get("phone"),
        designation=payload.get("designation"),
        team=payload.get("team"),
        supervisor=payload.get("supervisor"),
        hashed_password=get_password_hash(payload["password"]),
        status=UserStatus.pending_self_otp,
        role=UserRole.employee,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    otp_code = generate_otp()
    otp = OneTimePassword(
        user_id=user.id,
        code=otp_code,
        purpose=OTPPurpose.self_registration,
        expires_at=otp_expiry(),
    )
    db.add(otp)
    db.commit()
    log_admin_notification("New employee registration", f"OTP for {user.email}: {otp_code}")
    return user


def verify_user_self_otp(db: Session, email: str, otp_code: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    otp = (
        db.query(OneTimePassword)
        .filter(
            OneTimePassword.user_id == user.id,
            OneTimePassword.code == otp_code,
            OneTimePassword.purpose == OTPPurpose.self_registration,
            OneTimePassword.consumed.is_(False),
            OneTimePassword.expires_at >= datetime.utcnow(),
        )
        .first()
    )
    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")
    otp.consumed = True
    user.status = UserStatus.pending_admin_approval
    db.commit()

    admin_otp_code = generate_otp()
    admin_otp = OneTimePassword(
        user_id=user.id,
        code=admin_otp_code,
        purpose=OTPPurpose.admin_approval,
        expires_at=otp_expiry(60),
    )
    db.add(admin_otp)
    db.commit()
    log_admin_notification("Approve new employee", f"OTP for {user.email}: {admin_otp_code}")
    return user


def admin_approve_user(db: Session, user_id: int, otp_code: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    otp = (
        db.query(OneTimePassword)
        .filter(
            OneTimePassword.user_id == user.id,
            OneTimePassword.code == otp_code,
            OneTimePassword.purpose == OTPPurpose.admin_approval,
            OneTimePassword.consumed.is_(False),
            OneTimePassword.expires_at >= datetime.utcnow(),
        )
        .first()
    )
    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")
    otp.consumed = True
    user.status = UserStatus.active
    db.commit()
    return user


def request_vendor_otp(db: Session, user: User) -> None:
    otp_code = generate_otp()
    otp = OneTimePassword(
        user_id=user.id,
        code=otp_code,
        purpose=OTPPurpose.vendor_unlock,
        expires_at=otp_expiry(),
    )
    db.add(otp)
    db.commit()
    log_admin_notification("Vendor form unlock", f"OTP for {user.email}: {otp_code}")


def validate_vendor_otp(db: Session, user: User, otp_code: str) -> None:
    otp = (
        db.query(OneTimePassword)
        .filter(
            OneTimePassword.user_id == user.id,
            OneTimePassword.code == otp_code,
            OneTimePassword.purpose == OTPPurpose.vendor_unlock,
            OneTimePassword.consumed.is_(False),
            OneTimePassword.expires_at >= datetime.utcnow(),
        )
        .first()
    )
    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vendor OTP")
    otp.consumed = True
    db.commit()


def create_vendor(db: Session, user: User, payload: VendorCreate) -> Vendor:
    vendor = Vendor(
        name=payload.name,
        category=payload.category,
        contact_person=payload.contact_person,
        phone=payload.phone,
        email=payload.email,
        gst_number=payload.gst_number,
        region=payload.region,
        status=VendorStatus.pending_approval,
        created_by=user.id,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    for rate in payload.rate_cards:
        vendor_rate = VendorRate(
            vendor_id=vendor.id,
            item_name=rate.item_name,
            description=rate.description,
            unit=rate.unit,
            rate=rate.rate,
            min_quantity=rate.min_quantity,
            setup_charges=rate.setup_charges,
            notes=rate.notes,
            category_tag=rate.category_tag or payload.category,
        )
        db.add(vendor_rate)
    db.add(
        VendorHistory(
            vendor_id=vendor.id,
            action="created",
            performed_by=user.id,
            notes="Submitted for approval",
        )
    )
    db.commit()
    log_admin_notification("Vendor approval", f"Vendor {vendor.name} awaiting approval")
    return vendor


def submit_vendor_update(db: Session, vendor: Vendor, user: User, notes: str) -> None:
    db.add(
        VendorHistory(
            vendor_id=vendor.id,
            action="update_submitted",
            performed_by=user.id,
            notes=notes,
        )
    )
    vendor.status = VendorStatus.pending_approval
    db.commit()


def _calculate_budget_item_totals(rate: float, quantity: float, days: float, gst: float) -> (float, float):
    subtotal = rate * quantity * max(days, 1)
    total = subtotal * (1 + (gst or 0) / 100)
    return subtotal, total


def create_budget(db: Session, user: User, payload: BudgetCreate) -> Budget:
    budget = Budget(
        client_name=payload.client_name,
        event_name=payload.event_name,
        event_type=payload.event_type,
        event_location=payload.event_location,
        event_dates=payload.event_dates,
        event_days=payload.event_days,
        remarks=payload.remarks,
        owner_id=user.id,
        status=BudgetStatus.draft,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    for item in payload.items:
        subtotal, total = _calculate_budget_item_totals(item.rate, item.quantity, item.days, item.gst_percentage)
        db.add(
            BudgetItem(
                budget_id=budget.id,
                category=item.category,
                item_name=item.item_name,
                vendor_id=item.vendor_id,
                rate=item.rate,
                quantity=item.quantity,
                unit=item.unit,
                days=item.days,
                gst_percentage=item.gst_percentage,
                subtotal=subtotal,
                total=total,
                notes=item.notes,
                is_override=item.is_override,
            )
        )
    db.add(
        BudgetHistory(
            budget_id=budget.id,
            action="created",
            performed_by=user.id,
            notes="Budget drafted",
        )
    )
    db.commit()
    db.refresh(budget)
    return budget


ELEMENT_SHEET_COLUMNS = {
    "category": ["Category", "Service Category"],
    "item": ["Item", "Element", "Item Name"],
    "vendor": ["Vendor", "Preferred Vendor"],
    "rate": ["Rate", "Unit Rate"],
    "quantity": ["Quantity", "Qty"],
    "unit": ["Unit", "UOM"],
    "days": ["Days", "No. of Days"],
    "gst": ["GST %", "GST"],
}


def _resolve_column(columns, possibilities):
    for option in possibilities:
        if option in columns:
            return option
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing column {possibilities[0]}")


def parse_element_sheet(db: Session, file: UploadFile, owner: User) -> List[dict]:
    filename, path = save_upload(file, "element_sheets")
    df = pd.read_excel(path)
    df = df.fillna(0)
    results = []
    columns = df.columns
    col_map = {key: _resolve_column(columns, opts) for key, opts in ELEMENT_SHEET_COLUMNS.items() if key != "gst"}
    gst_column = None
    for option in ELEMENT_SHEET_COLUMNS["gst"]:
        if option in columns:
            gst_column = option
            break
    for _, row in df.iterrows():
        category = str(row[col_map["category"]]).strip() or "General"
        item_name = str(row[col_map["item"]]).strip()
        if not item_name:
            continue
        vendor_name = str(row[col_map["vendor"]]).strip()
        unit = str(row[col_map["unit"]]).strip() or "unit"
        rate = float(row[col_map["rate"]]) if row[col_map["rate"]] else 0
        quantity = float(row[col_map["quantity"]]) if row[col_map["quantity"]] else 0
        days = float(row[col_map["days"]]) if row[col_map["days"]] else 1
        gst_percentage = float(row[gst_column]) if gst_column and row[gst_column] else 0

        vendor = None
        if vendor_name:
            vendor = db.query(Vendor).filter(Vendor.name.ilike(f"%{vendor_name}%"), Vendor.status == VendorStatus.approved).first()
        if not vendor:
            vendor = (
                db.query(Vendor)
                .join(VendorRate)
                .filter(
                    VendorRate.item_name.ilike(f"%{item_name}%"),
                    Vendor.status == VendorStatus.approved,
                    VendorRate.category_tag.ilike(f"%{category}%"),
                )
                .first()
            )
        vendor_id = vendor.id if vendor else None
        if vendor and rate == 0:
            rate_card = (
                db.query(VendorRate)
                .filter(VendorRate.vendor_id == vendor.id, VendorRate.item_name.ilike(f"%{item_name}%"))
                .first()
            )
            if rate_card:
                rate = rate_card.rate
                unit = rate_card.unit
        subtotal, total = _calculate_budget_item_totals(rate, quantity or 1, days or 1, gst_percentage)
        results.append(
            {
                "category": category or "General",
                "item_name": item_name,
                "vendor_id": vendor_id,
                "rate": rate or 0,
                "quantity": quantity or 1,
                "unit": unit or "unit",
                "days": days or 1,
                "gst_percentage": gst_percentage or 0,
                "notes": f"Auto-imported from {filename}",
                "is_override": False,
                "subtotal": subtotal,
                "total": total,
            }
        )
    db.add(
        ActivityLog(
            entity="budget_import",
            entity_id=0,
            action="parsed_element_sheet",
            performed_by=owner.id,
            details=f"Imported {len(results)} items from {filename}",
        )
    )
    db.commit()
    return results


def attach_budget_document(db: Session, budget: Budget, file: UploadFile, document_type: str) -> BudgetDocument:
    filename, path = save_upload(file, "budgets", str(budget.id))
    document = BudgetDocument(
        budget_id=budget.id,
        filename=filename,
        path=path,
        document_type=document_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def submit_budget_for_approval(db: Session, budget: Budget, user: User) -> Budget:
    if budget.status not in {BudgetStatus.draft, BudgetStatus.returned}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Budget already submitted")
    budget.status = BudgetStatus.under_review
    db.add(
        BudgetHistory(
            budget_id=budget.id,
            action="submitted",
            performed_by=user.id,
            notes="Submitted for approval",
        )
    )
    approval = Approval(
        budget_id=budget.id,
        stage=ApprovalStage.approver,
        status="pending",
        approver_id=None,
    )
    db.add(approval)
    db.commit()
    return budget


def process_approval(db: Session, approval: Approval, approver: User, approve: bool, comments: Optional[str]) -> Budget:
    approval.status = "approved" if approve else "returned"
    approval.approver_id = approver.id
    approval.decided_at = datetime.utcnow()
    approval.comments = comments
    db.commit()

    budget = approval.budget
    if approve:
        if approval.stage == ApprovalStage.approver:
            next_stage = ApprovalStage.accounts
            db.add(
                Approval(
                    budget_id=budget.id,
                    stage=next_stage,
                    status="pending",
                )
            )
            budget.status = BudgetStatus.under_review
        elif approval.stage == ApprovalStage.accounts:
            next_stage = ApprovalStage.finalized
            db.add(
                Approval(
                    budget_id=budget.id,
                    stage=next_stage,
                    status="approved",
                    approver_id=approver.id,
                    decided_at=datetime.utcnow(),
                )
            )
            budget.status = BudgetStatus.approved
    else:
        budget.status = BudgetStatus.returned
    db.commit()
    return budget

