# Vyrenzo Bank — AI-Powered Banking Intelligence Platform

Vyrenzo Bank is a next-generation banking intelligence platform designed to automate the extraction, analysis, and reconciliation of complex banking data. It leverages **Gemini 2.5 Flash Lite** for intelligent OCR and classification, a modular **Python Computation Engine** for financial accuracy, and a modern **Next.js 16** frontend for a premium user experience.

---

## 🏗️ Architecture Overview

The project is structured as a modular Monorepo:

### 1. **Backend (`backend/`)** — *The Brains*
Powered by **FastAPI**, it handles the heavy lifting through a discrete 3-stage pipeline:
- **Stage 1 (Extraction & Classification)**: Recognizes bank-specific PDF formats, classifies accounts, and extracts transactional data with high-confidence OCR.
- **Stage 2 (Computation)**: Processes raw data through our verified formula engine (CC Interest, WCDL, Forex Excess, ROI Verification).
- **Stage 3 (Reporting)**: Generates automated Working Sheets and Management Reports in Excel format.

### 2. **Frontend (`frontend/`)** — *The UI*
Powered by **Next.js 16** and **Tailwind CSS**:
- **Smart Proxy**: A custom Next.js API route that intelligently maps legacy frontend calls (CamelCase) to our modern Python API (snake_case).
- **Protected Environment**: Full auth-gated dashboard for document management, pipeline monitoring, and report downloads.
- **Dynamic Visualization**: Real-time progress tracking for background OCR and computation runs.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.13+**
- **Node.js 20+**
- **PostgreSQL 16+**
- **Gemini API Key** (from Google AI Studio)

### 2. Backend Setup
```bash
cd backend
# Copy and update your environment variables
cp .env.example .env
# Install dependencies
pip install -r requirements.txt
# Start the server
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
# Copy and update your environment variables
cp .env.example .env.local
# Install dependencies
npm install
# Start the development server
npm run dev
```

---

## 🗄️ Database Setup

To run the database for the first time, follow these steps to ensure your PostgreSQL instance is ready and the schema is correctly applied.

### 1. Create the Database
In your PostgreSQL tool (PGAdmin, DBeaver, or `psql`), create the database:
```sql
CREATE DATABASE fincore_dev;
```

### 2. Apply the Schema
Apply the schema script located at `backend/database/schema.sql` to your new database.

**Via Command Line (`psql`):**
```powershell
cd backend
psql -U postgres -d fincore_dev -f database/schema.sql
```
*(Default password is `Bharadwaj2112` unless changed in your local Postgres setup)*

### 3. Verify Connection
Ensure your `backend/.env` file has the correct `DATABASE_URL`:
```env
DATABASE_URL=postgresql://postgres:Bharadwaj2112@localhost:5432/fincore_dev
```

**What this setup includes:**
- **UUIDs**: Enabled for secure, unique record IDs.
- **Enums**: Pre-defined roles (`ADMIN`, `ANALYST`) and statuses (`UPLOADED`, `PENDING`).
- **Tables**: `Organisation`, `User`, `Upload`, `PipelineRun`, `AuditLog`.
- **Seed Data**: Automatically creates a default organization (`Vyrenzo Bank Demo`).

> [!NOTE]
> Since the platform uses **Firebase Auth**, your first login will create a Firebase user. Ensure your email is linked to an organization in the `User` table to access protected routes.

---

## 📂 Directory Structure

### Backend (`backend/app/`)
- `api/v1/`: Modular routers for uploads, pipeline, and reports.
- `computation/`: Pure Python formula engine (zero-dependency, highly testable).
- `ocr/`: LLM-based extraction agents and bank classifiers.
- `pipeline/`: Graph-based orchestrator that manages the multi-stage lifecycle.
- `excel/`: Automated Excel builders for Statements, Working Sheets, and Banking Reports.
- `services/`: Infrastructure adapters (S3, Forex Rates, Validation).
- `core/`: Central configuration and database connection pooling.

### Frontend (`frontend/app/`)
- `(auth)/`: Login and registration flows.
- `(protected)/`: Auth-gated routes for Dashboard, Uploads, Documents, Reports, and Forex Analysis.
- `api/[...path]/`: Our custom **Smart Proxy** for backend communication.
- `components/`: Modular UI units (Sidebar, TopBar, DropZones, PipelineStatus).
- `lib/`: Shared API clients and utility constants.

---

## 🧪 Testing & Validation
The platform includes a robust validation engine that cross-references computed interest against bank-stated values across 5 critical dimensions:
- CC Interest Reconciliation
- WCDL Interest Calculation
- ROI Deviation Analysis
- Forex Rate Verification
- Limit Utilisation Checks

Run the computation test suite:
```bash
cd backend
python -m pytest tests/ -v
```

---

## 🛡️ Future-Proof Design
- **Scalable DB**: Modular PostgreSQL schema with built-in Audit Logs and multi-tenant support (via `orgId`).
- **Dynamic OCR**: Easy to add support for new banks by simply updating the Regex Classifiers in `app/ocr/classifier.py`.
- **Hybrid Storage**: Seamlessly switch between local filesystem and AWS S3 via the `USE_LOCAL_STORAGE` flag.

---
**Vyrenzo Bank** — *Automating Financial Intelligence.*