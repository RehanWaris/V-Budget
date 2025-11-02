# Node.js Guided Workflow

This minimal TypeScript-free Node.js script demonstrates how to interact with the
V-Budget API from the command line. It performs the full employee activation and
vendor onboarding cycle using the new `/debug/otps` helper endpoint.

## Prerequisites

- Node.js 18 or later (for the built-in `fetch` API).
- The FastAPI server running locally (use `scripts/run_api.sh`).

## Usage

```bash
cd samples/node-workflow
node demo.mjs
```

Optional environment variables:

- `VBUDGET_BASE_URL` – override the API base URL (default `http://localhost:8000`).
- `VBUDGET_ADMIN_EMAIL` – admin login email (default `rehan@voiceworx.in`).
- `VBUDGET_ADMIN_PASSWORD` – admin password (default `Admin@123`).

The script will stop on the first failure and print the underlying API response
so you can diagnose missing approvals or OTP codes.
