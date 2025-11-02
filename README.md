# V-Budget Platform

V-Budget is an API-first event budgeting platform tailored for Indian experiential marketing teams. This repository contains a FastAPI backend that covers employee onboarding, vendor catalogues, budgeting workflows, and approval stages.

## Features

- Email + password registration with two-step OTP activation (self verification followed by admin approval routed to `rehan@voiceworx.in`).
- JWT-based authentication with role-aware access (Employee, Approver, Accounts, Admin).
- Vendor onboarding with OTP gate, category tagging, rate cards, and approval lifecycle.
- Budget creation from manual entries or Excel element sheets with automatic vendor rate lookups and GST totals.
- Multi-stage approval pipeline (Preparer → Approver → Accounts → Finalised) with activity logging.
- Document uploads for briefs, rate cards, and budget artefacts.
- Dashboard metrics for quick operational insight.

## Project Structure

```
app/
├── config.py          # Environment-aware settings
├── database.py        # SQLAlchemy engine/session management
├── deps.py            # Authentication helpers and dependencies
├── main.py            # FastAPI application with all routes
├── models.py          # SQLAlchemy ORM models
├── schemas.py         # Pydantic request/response models
├── security.py        # Password hashing & JWT helpers
├── services.py        # Business logic for OTP, vendors, budgets, approvals
├── utils.py           # Shared helpers (OTP generator, file uploads, etc.)
└── __init__.py
```

## Prerequisites

- Python 3.11+
- `pip` package manager

## Local Setup

1. **Create and activate a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations** (tables auto-create on first start)

4. **Launch the API server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Open the interactive docs**
   Visit [http://localhost:8000/docs](http://localhost:8000/docs) to explore and test endpoints.

### Running inside GitHub Codespaces

Codespaces exposes forwarded ports rather than `localhost`. After starting the
server with the command above, open the **Ports** tab in the Codespaces UI and
locate port `8000`. Choose **Open in Browser** (or copy the provided HTTPS
URL). Append `/docs` to that URL to view the interactive Swagger UI. This is
equivalent to visiting `http://localhost:8000/docs` on a local machine.

## First-Time Admin Login

On the first run the system seeds an admin account:

- **Email:** `rehan@voiceworx.in`
- **Password:** `Admin@123`

Change the password immediately after logging in. Use this account to approve pending employees and vendors.

## Core Workflows

### Employee Registration & Activation

1. Employee calls `POST /auth/register` with name, email, and password. Console logs print an OTP for self-verification.
2. Employee calls `POST /auth/verify-self` with the emailed OTP. The system now awaits admin approval.
3. Admin retrieves pending accounts via `GET /users/pending` and calls `POST /auth/admin-approve` with the second OTP (logged for demo) to activate the user.
4. Activated users authenticate via `POST /auth/login` (OAuth2 password flow) to receive a JWT.

### Vendor Onboarding

1. Authenticated user requests an OTP with `POST /vendors/request-otp`.
2. After receiving the OTP (console log), user submits vendor details and rate cards through `POST /vendors`.
3. Approvers review and approve vendors using `POST /vendors/{vendor_id}/approve`.
4. Approved vendors surface in dropdowns and cost sheets.

### Budget Creation & Approvals

1. Users can import an element sheet using `POST /budgets/import` (Excel). The API auto-detects categories, vendors, rates, and GST.
2. Use the resulting items when posting `POST /budgets` to create a draft.
3. Upload supplementary documents with `POST /budgets/{id}/documents`.
4. Submit for approval via `POST /budgets/{id}/submit`.
5. Approvers and accounts act on pending approvals using `POST /approvals` with the appropriate stage (`approver` or `accounts`).
6. Once both stages approve, the budget status becomes `approved`; otherwise it returns to the preparer with comments.

### Dashboard

`GET /dashboard/metrics` returns counts for pending approvals, approved budgets, in-flight events, and vendors awaiting approval.

## Deployment Guide

### Container Image (Optional)

1. Build image:
   ```bash
   docker build -t vbudget-api .
   ```
2. Run container:
   ```bash
   docker run -d -p 8000:8000 --name vbudget vbudget-api
   ```

### Production Checklist

- Configure environment variables (`VBUDGET_SECRET_KEY`, `VBUDGET_DATABASE_URL`, `VBUDGET_ADMIN_EMAIL`).
- Use PostgreSQL or MySQL for production workloads.
- Terminate TLS at a reverse proxy (Nginx/Traefik) and forward to Uvicorn/Gunicorn workers.
- Set up a real mailer (SES, SendGrid) inside `utils.log_admin_notification`.
- Use S3 or Azure Blob for document storage in place of local filesystem if running across multiple nodes.

## Testing the API

1. Run the health check:
   ```bash
   curl http://localhost:8000/health
   ```
2. Execute unit/integration tests as you add them (placeholder, none included yet).

## Next Steps

- Add a dedicated frontend (React/Next.js) using these endpoints.
- Wire third-party email/SMS OTP delivery.
- Extend analytics endpoints and integrate with BI tools.

Happy budgeting! 🎉
