from datetime import timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .deps import get_current_user, require_role
from .models import (
    Approval,
    ApprovalStage,
    Budget,
    BudgetStatus,
    OneTimePassword,
    OTPPurpose,
    User,
    UserRole,
    UserStatus,
    Vendor,
    VendorStatus,
)
from .schemas import (
    AdminOTPRequest,
    ApprovalAction,
    BudgetCreate,
    BudgetResponse,
    BudgetItemResponse,
    DashboardMetrics,
    Message,
    OTPRequest,
    Token,
    UserCreate,
    UserResponse,
    VendorCreateRequest,
    VendorResponse,
)
from .security import create_access_token, get_password_hash, needs_rehash, verify_password
from .services import (
    admin_approve_user,
    attach_budget_document,
    create_budget,
    create_vendor,
    parse_element_sheet,
    process_approval,
    register_user,
    request_vendor_otp,
    seed_admin,
    submit_budget_for_approval,
    validate_vendor_otp,
    verify_user_self_otp,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        seed_admin(db, settings.admin_email)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing_page() -> str:
    docs_url = "/docs"
    debug_section = ""
    if settings.debug_mode:
        debug_section = """
            <li>
              Visit <code>/debug/otps</code> to see OTP codes generated for demo purposes.
              Filter them by adding <code>?email=&lt;your email&gt;</code> or
              <code>?purpose=self_registration</code> to the URL.
            </li>
        """

    return f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <title>V-Budget API</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.6; color: #1f2933; }}
          code {{ background: #f1f5f9; padding: 0.15rem 0.35rem; border-radius: 4px; }}
          ol {{ max-width: 720px; }}
          .note {{ background: #ecfeff; border-left: 4px solid #0891b2; padding: 1rem; margin-top: 1.5rem; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <h1>V-Budget API is running</h1>
        <p>The interactive documentation lives at <a href=\"{docs_url}\">{docs_url}</a>.</p>
        <h2>Quick start</h2>
        <ol>
          <li>Open the <a href=\"{docs_url}\">Swagger UI</a> and expand <strong>POST /auth/login</strong>.</li>
          <li>Sign in with the seeded admin account <code>rehan@voiceworx.in</code> / <code>Admin@123</code> and click the green <strong>Authorize</strong> button.</li>
          <li>Create additional employees with <strong>POST /auth/register</strong> and activate them using the OTP endpoints.</li>
          <li>Once an employee is active, explore vendor and budget endpoints to build costing sheets.</li>
          {debug_section}
        </ol>
        <div class=\"note\">
          <strong>Need automation?</strong> Run <code>scripts/run_api.sh</code> from the repository root to install
          dependencies and launch the server in one step. Use the sample workflow under <code>samples/node-workflow</code>
          for an end-to-end demonstration of registration, approval, and vendor creation.
        </div>
      </body>
    </html>
    """


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    new_user = register_user(db, user.model_dump())
    return new_user


@app.post("/auth/verify-self", response_model=Message)
def verify_self(request: OTPRequest, db: Session = Depends(get_db)):
    verify_user_self_otp(db, request.email, request.otp)
    return Message(detail="Email verified. Await admin approval.")


@app.post("/auth/admin-approve", response_model=UserResponse)
def admin_approve(request: AdminOTPRequest, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.admin, UserRole.approver))):
    user = admin_approve_user(db, request.user_id, request.otp)
    return user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not active")

    if needs_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(form_data.password)
        db.commit()
        db.refresh(user)
    access_token = create_access_token(user.email, expires_delta=timedelta(minutes=settings.access_token_expire_minutes))
    return Token(access_token=access_token)


@app.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/users/pending", response_model=List[UserResponse])
def pending_users(db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.admin, UserRole.approver))):
    return db.query(User).filter(User.status == UserStatus.pending_admin_approval).all()


@app.get("/debug/otps")
def list_debug_otps(
    email: Optional[str] = None,
    purpose: Optional[OTPPurpose] = None,
    db: Session = Depends(get_db),
):
    if not settings.debug_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    query = db.query(OneTimePassword).filter(OneTimePassword.consumed.is_(False))
    if email:
        query = query.join(User).filter(User.email == email)
    if purpose:
        query = query.filter(OneTimePassword.purpose == purpose)

    otps = query.order_by(OneTimePassword.created_at.desc()).all()
    return [
        {
            "user_id": otp.user_id,
            "email": otp.user.email if otp.user else None,
            "purpose": otp.purpose.value,
            "code": otp.code,
            "expires_at": otp.expires_at.isoformat(),
            "created_at": otp.created_at.isoformat(),
        }
        for otp in otps
    ]


@app.post("/vendors/request-otp", response_model=Message)
def request_vendor_access(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    request_vendor_otp(db, current_user)
    return Message(detail="OTP sent to admin. Provide the OTP to continue.")


@app.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor_endpoint(
    request: VendorCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    validate_vendor_otp(db, current_user, request.otp)
    vendor = create_vendor(db, current_user, request.vendor)
    return vendor


@app.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    status_filter: Optional[VendorStatus] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Vendor)
    if status_filter:
        query = query.filter(Vendor.status == status_filter)
    if category:
        query = query.filter(Vendor.category.ilike(f"%{category}%"))
    return query.order_by(Vendor.updated_at.desc()).all()


@app.get("/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@app.post("/vendors/{vendor_id}/approve", response_model=VendorResponse)
def approve_vendor(vendor_id: int, approve: bool = True, db: Session = Depends(get_db), _: User = Depends(require_role(UserRole.admin, UserRole.approver))):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    vendor.status = VendorStatus.approved if approve else VendorStatus.rejected
    db.commit()
    db.refresh(vendor)
    return vendor


@app.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget_endpoint(payload: BudgetCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    budget = create_budget(db, current_user, payload)
    return budget


@app.post("/budgets/{budget_id}/submit", response_model=BudgetResponse)
def submit_budget(budget_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can submit budget")
    submit_budget_for_approval(db, budget, current_user)
    db.refresh(budget)
    return budget


@app.get("/budgets", response_model=List[BudgetResponse])
def list_budgets(
    status_filter: Optional[BudgetStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return budgets visible to the current user."""

    def _scoped_query() -> "Query[Budget]":
        base_query = db.query(Budget)
        if current_user.role != UserRole.admin:
            return base_query.filter(Budget.owner_id == current_user.id)
        return base_query

    query = _scoped_query()
    if status_filter is not None:
        query = query.filter(Budget.status == status_filter)
    return query.order_by(Budget.updated_at.desc()).all()


@app.get("/budgets/{budget_id}", response_model=BudgetResponse)
def get_budget(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if current_user.role != UserRole.admin and budget.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    return budget


@app.post("/budgets/{budget_id}/documents", response_model=Message)
def upload_budget_document(
    budget_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.owner_id != current_user.id and current_user.role not in {UserRole.admin, UserRole.approver, UserRole.accounts}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")
    attach_budget_document(db, budget, file, document_type)
    return Message(detail="Document uploaded")


@app.post("/budgets/import", response_model=List[BudgetItemResponse])
def import_budget_items(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = parse_element_sheet(db, file, current_user)
    return [BudgetItemResponse(**item) for item in items]


@app.post("/approvals", response_model=BudgetResponse)
def act_on_approval(
    action: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.approver, UserRole.accounts, UserRole.admin)),
):
    approval = (
        db.query(Approval)
        .filter(
            Approval.budget_id == action.budget_id,
            Approval.stage == action.stage,
            Approval.status == "pending",
        )
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    budget = process_approval(db, approval, current_user, action.approve, action.comments)
    db.refresh(budget)
    return budget


@app.get("/dashboard/metrics", response_model=DashboardMetrics)
def dashboard_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pending = db.query(Budget).filter(Budget.status == BudgetStatus.under_review).count()
    active = db.query(Budget).filter(Budget.status == BudgetStatus.approved).count()
    upcoming = db.query(Budget).filter(Budget.status != BudgetStatus.approved).count()
    vendor_updates = db.query(Vendor).filter(Vendor.status == VendorStatus.pending_approval).count()
    return DashboardMetrics(
        pending_approvals=pending,
        active_budgets=active,
        upcoming_events=upcoming,
        recent_vendor_updates=vendor_updates,
    )


@app.get("/health", response_model=Message)
def healthcheck():
    return Message(detail="OK")
