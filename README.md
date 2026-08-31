# FinCore — AI-Powered Financial Intelligence Platform

> Automating bank statement extraction, financial reconciliation, and management reporting for accounting and finance teams.

---

## Problem Statement

Financial analysts at firms managing large working capital facilities spend significant time manually processing bank statements. PDF documents from multiple banks arrive in inconsistent, proprietary formats. Analysts must hand-extract transaction data, compute interest on Cash Credit (CC) accounts and Working Capital Demand Loans (WCDL), reconcile bank-stated figures against their own calculations, check Forex exposure, verify ROI deviation, and assemble Excel reports — all manually, all error-prone, all at scale.

This process introduces compounding risk: a single mis-read figure propagates through every downstream reconciliation. Turnaround time for a full monthly review is measured in days.

---

## Solution

FinCore is a full-stack financial intelligence platform that replaces the manual workflow with an automated, auditable pipeline. A finance team uploads bank statements; FinCore classifies the documents, extracts structured transaction data using a large language model, runs a deterministic computation engine across all financial dimensions, and produces verified Working Sheets and Management Reports in Excel format — ready for review.

The system is multi-tenant, role-controlled, and fully audited. Every processing event is traceable from upload to final report.

---

## Key Product Capabilities

| Capability | Detail |
|---|---|
| **Intelligent Document Extraction** | Classifies bank-specific PDF formats using regex-based classifiers; extracts transactions via Gemini 2.5 Flash Lite OCR |
| **CC Interest Reconciliation** | Computes Cash Credit interest and reconciles against bank-stated figures |
| **WCDL Interest Calculation** | Calculates Working Capital Demand Loan interest with date-accurate accrual |
| **ROI Deviation Analysis** | Flags deviations between expected and actual return on investment |
| **Forex Rate Verification** | Cross-checks Forex transaction rates against reference rates |
| **Limit Utilisation Checks** | Validates drawings against sanctioned credit limits |
| **Automated Reporting** | Generates structured Excel Working Sheets and Management Reports |
| **Multi-Tenant RBAC** | Organisation-scoped access with role-based permission enforcement |
| **Audit Logging** | Every user action and pipeline event written to an immutable audit log |

---

## End-to-End Processing Flow

```
Upload (PDF)
    │
    ▼
Stage 1 — Extraction & Classification
    ├── Bank format classifier (regex pattern matching)
    ├── Gemini 2.5 Flash Lite OCR extraction
    └── Structured transaction data → PostgreSQL
    │
    ▼
Stage 2 — Computation
    ├── CC Interest calculation
    ├── WCDL interest calculation
    ├── ROI deviation analysis
    ├── Forex rate verification
    └── Limit utilisation checks
    │
    ▼
Stage 3 — Reporting
    ├── Excel Working Sheet generation (openpyxl)
    └── Management Report generation
    │
    ▼
Download / Review (Next.js Dashboard)
```

The computation stage is intentionally **decoupled from the LLM**. The LLM handles unstructured extraction only; all financial calculations are executed by a pure-Python, zero-dependency formula engine, making them deterministic, reproducible, and independently testable.

---

## Architecture

FinCore uses a **split-stack monorepo** with separate deployment targets for the frontend and backend.

### Frontend — Next.js 16 (App Router)
- React dashboard with real-time pipeline progress tracking
- Firebase Authentication (client-side ID token issuance)
- Next.js Middleware as an API proxy: routes all `/api/v1/*` requests to the FastAPI backend, preserving authentication headers and providing a consistent API boundary
- Protected routes enforce authentication and permission checks before rendering

### Backend — FastAPI (Python 3.12)
- Stateless REST API serving the pipeline and reporting
- Firebase Admin SDK for server-side ID token verification
- Internal `User` records in PostgreSQL mapped to Firebase UIDs; email-based fallback for account linking
- 3-stage graph-based pipeline orchestrator managing lifecycle state per upload
- Pure-Python computation engine (no ORM, raw `psycopg2` for query control)
- Storage abstracted behind a provider interface supporting local disk and S3-compatible object storage

### Data Layer
- **PostgreSQL**: Schema with `Organisation`, `User`, `Upload`, `PipelineRun`, `AuditLog` tables; UUID primary keys; enum-typed state columns; foreign key constraints enforcing org-level tenancy
- **Object Storage**: PDF uploads and generated Excel reports stored via an abstracted provider (local or S3)

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, React 18, TypeScript, Tailwind CSS, Zustand |
| **Backend** | Python 3.12, FastAPI, uvicorn |
| **Database** | PostgreSQL (psycopg2 — raw SQL, no ORM) |
| **AI / OCR** | Google Gemini 2.5 Flash Lite (`google-generativeai`) |
| **Authentication** | Firebase Auth (ID Tokens + Firebase Admin SDK) |
| **Reporting** | openpyxl, pandas |
| **PDF Processing** | pdfplumber, pypdf, pdf2image, pytesseract |
| **Object Storage** | AWS S3 (boto3) / local filesystem (abstracted) |
| **CI/CD** | GitHub Actions |
| **Hosting** | Vercel (frontend), Railway (backend), Supabase (PostgreSQL) |

---

## Key Engineering Decisions

**Deterministic computation, separate from the LLM**
The LLM is used only for unstructured data extraction. All financial calculations — CC interest, WCDL, ROI, Forex, limit checks — are executed by a pure Python formula engine. This separation means the computation layer is independently testable, produces reproducible results, and is not subject to LLM non-determinism.

**Raw SQL over ORM**
The backend uses `psycopg2` with hand-written SQL rather than SQLAlchemy or another ORM. This gives precise control over query structure, makes query plans predictable, and avoids the abstraction overhead that can introduce subtle bugs in financial data pipelines.

**API proxy boundary in the frontend**
The Next.js middleware layer proxies all backend calls, so the FastAPI service is never directly exposed to the client. Authentication headers are forwarded intact, and the backend URL is kept server-side. This provides a clean and consistent API surface without requiring a separate gateway service.

**Extensible bank classifier**
Bank-specific PDF formats are identified by regex-based classifiers in `app/ocr/classifier.py`. Adding support for a new bank requires only a new classifier entry — no changes to the pipeline orchestrator or computation engine.

**Storage abstraction**
Storage I/O is behind a provider interface. Switching between local storage and S3-compatible object storage is controlled by a single environment flag. This made local development and cloud deployment interchangeable without modifying application logic.

**Firebase Auth with internal user linking**
Firebase issues ID tokens; the backend verifies them and maps them to an internal `User` record in PostgreSQL. If a Firebase UID is not found, the system falls back to an email-based lookup and updates the record's `firebaseUid` field. This prevents duplicate-key constraint violations when migrating existing users and makes the authentication layer resilient to re-registration events.

---

## Authentication, RBAC, and Multi-Tenant Design

```
Firebase Auth (client)
    │  ID Token (JWT)
    ▼
Next.js Middleware (proxy, header forwarding)
    │
    ▼
FastAPI — firebase_admin.verify_id_token()
    │
    ▼
PostgreSQL User lookup (by firebaseUid → email fallback)
    │
    ├── orgId   → scopes all data queries to the user's organisation
    ├── roleId  → determines permission set
    └── permissions → enforced on every protected endpoint
```

- **Multi-tenancy**: Every table with user-facing data carries an `orgId` foreign key. Queries are scoped by organisation at the service layer, not the application layer.
- **Roles**: Pre-defined `ADMIN` and `ANALYST` roles with distinct permission sets.
- **Audit Log**: Every significant action (upload, pipeline trigger, report download, admin change) is appended to an `AuditLog` table with user, timestamp, and action metadata.

---

## CI/CD and Deployment Workflow

### Continuous Integration — GitHub Actions

A CI workflow runs on every push and pull request targeting `develop` and `main`.

**Frontend CI job:**
1. Node.js 20, `npm ci` (locked from `package-lock.json`)
2. ESLint (flat config with `eslint-config-next/core-web-vitals`)
3. `next build` (full production build verification)

**Backend CI job:**
1. Python 3.12, `pip install -r requirements.txt`
2. `pytest tests/ -v`

Dependency caching (npm and pip) is enabled for both jobs to minimise build times.

### Production Deployment

| Service | Platform | Trigger |
|---|---|---|
| Frontend | **Vercel** | Auto-deploy on push to `main`; preview deployments on every PR |
| Backend API | **Railway** | Auto-deploy on push to `main` |
| Database | **Supabase** | Managed PostgreSQL; schema applied via `backend/database/schema.sql` |

The Next.js middleware reads `NEXT_PUBLIC_BACKEND_URL` at build time to point at the Railway backend. No hardcoded URLs appear in source code.

---

## Skills Demonstrated

- **Full-stack development**: End-to-end ownership of a production application spanning React/Next.js frontend and Python/FastAPI backend.
- **AI / LLM integration**: Practical use of Gemini 2.5 Flash Lite for structured extraction from unstructured document inputs.
- **Financial domain engineering**: Implementing and verifying financial computation logic (interest, Forex, ROI, limit checks) with correctness as the primary constraint.
- **Authentication and security**: Firebase Auth integration, server-side token verification, internal user mapping, email fallback linking, and RBAC enforcement.
- **Database design**: Schema design with multi-tenant constraints, UUID keys, enum state management, audit logging, and raw SQL for query control.
- **API design**: RESTful API design with FastAPI, typed request/response models, and a clean proxy boundary.
- **CI/CD**: GitHub Actions workflow design with caching, lint, build, and test gates.
- **Cloud deployment**: Multi-service production architecture across Vercel, Railway, and Supabase with environment-separated configurations.
- **Infrastructure debugging**: Diagnosing and resolving production routing failures, authentication errors, and deployment configuration issues.
- **Testing**: Backend pytest suite and frontend build verification as CI gates.

---

## My Contribution

My work on FinCore covered frontend–backend integration, authentication hardening, production infrastructure, and CI/CD setup.

- **Authentication & Security**: Designed the backend authentication flow in `app/core/security.py` — Firebase ID token verification, internal `User` lookup by `firebaseUid`, email-based fallback linking to handle account migrations, and `orgId`/`roleId`/permission propagation to every authenticated request. Resolved a production duplicate-key constraint failure caused by re-registration of an existing email.

- **Production Routing**: Diagnosed and fixed a Vercel → Railway routing failure caused by a legacy `/_/backend` prefix in the Next.js API proxy route. Removed the deprecated prefix and aligned proxy configuration with the production Railway URL.

- **Middleware & Proxy Configuration**: Audited and corrected the Next.js middleware layer. Disabled an HTTP Basic Auth challenge that was triggering native browser authentication popups in production. Cleaned up a stale root-level `vercel.json` that was conflicting with Vercel's automatic Next.js detection.

- **CI/CD**: Designed and implemented the GitHub Actions CI pipeline — separate Frontend CI and Backend CI jobs, dependency caching for both npm and pip, ESLint flat config setup using `eslint-config-next` via `FlatCompat`, and production build verification as a CI gate.

- **ESLint Configuration**: Migrated linting from the deprecated `next lint` CLI wrapper (removed in Next.js 16) to a proper ESLint flat config (`eslint.config.mjs`) using `FlatCompat` to wrap the legacy `eslint-config-next` package without adding new dependencies.

- **Database Auditing**: Audited the PostgreSQL schema and backend connection configuration. Documented table structure, constraints, indexes, and seed data. Verified compatibility with Supabase as the production database provider.

- **README / Portfolio Documentation**: Authored product-level documentation accurately reflecting implemented capabilities, architecture, engineering decisions, and contribution scope.

---

## Current Product Status

**Implemented and verified:**
- ✅ Firebase Authentication and PostgreSQL-backed internal user system
- ✅ Multi-tenant organisation model with RBAC and audit logging
- ✅ 3-stage pipeline: document extraction → financial computation → report generation
- ✅ Gemini 2.5 Flash Lite integration for OCR/extraction
- ✅ CC interest, WCDL, ROI deviation, Forex verification, limit utilisation computation
- ✅ Excel Working Sheet and Management Report generation
- ✅ Next.js 16 App Router dashboard with pipeline monitoring
- ✅ Production deployment: Vercel + Railway + Supabase
- ✅ GitHub Actions CI (lint, build, test)

**Planned:**
- ⏳ Open banking API integration for automated statement ingestion
- ⏳ Advanced anomaly detection on extracted transactions
- ⏳ Real-time collaborative annotation
- ⏳ Expanded multi-currency Forex reconciliation coverage

---

## Impact

FinCore replaces a multi-day manual process with a minutes-long automated pipeline. For a finance team managing multiple credit facilities across several banks, this means faster month-end closes, fewer calculation errors, and a fully auditable trail from raw document to final report. The architecture is designed to scale: adding a new bank requires one classifier; adding a new computation type requires one formula function; adding a new organisation requires one database row.

<!-- Screenshots placeholder -->
<!-- ![Dashboard](./docs/screenshots/dashboard.png) -->
<!-- ![Pipeline Monitor](./docs/screenshots/pipeline.png) -->
<!-- ![Report Output](./docs/screenshots/report.png) -->