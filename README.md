# Vyrenzo Bank — AI-Powered Banking Intelligence Platform

Vyrenzo Bank is a next-generation banking intelligence platform designed to automate the extraction, analysis, and reconciliation of complex banking data. It leverages **Gemini 2.5 Flash Lite** for intelligent OCR and classification, a modular **Python Computation Engine** for financial accuracy, and a modern **Next.js 16** frontend for a premium user experience.

---

## 🏗️ Architecture Overview

The project is structured as a modular Monorepo:

### 1. **Backend (`fincore-backend/`)** — *The Brains*
Powered by **FastAPI**, it handles the heavy lifting through a discrete 3-stage pipeline:
- **Stage 1 (Extraction & Classification)**: Recognizes bank-specific PDF formats, classifies accounts, and extracts transactional data with high-confidence OCR.
- **Stage 2 (Computation)**: Processes raw data through our verified formula engine (CC Interest, WCDL, Forex Excess, ROI Verification).
- **Stage 3 (Reporting)**: Generates automated Working Sheets and Management Reports in Excel format.

### 2. **Frontend (`fincore-frontend/`)** — *The UI*
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
cd fincore-backend
# Copy and update your environment variables
cp .env.example .env
# Install dependencies
pip install -r requirements.txt
# Initialize Database Schema
python scripts/init_db.py
# Start the server
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd fincore-frontend
# Copy and update your environment variables
cp .env.example .env.local
# Install dependencies
npm install
# Start the development server
npm run dev
```

---

## 📂 Directory Structure

### Backend (`app/`)
- `api/v1/`: Modular routers for uploads, pipeline, and reports.
- `computation/`: Pure Python formula engine (zero-dependency, highly testable).
- `ocr/`: LLM-based extraction agents and bank classifiers.
- `pipeline/`: Graph-based orchestrator that manages the multi-stage lifecycle.
- `excel/`: Automated Excel builders for Statements, Working Sheets, and Banking Reports.
- `services/`: Infrastructure adapters (S3, Forex Rates, Validation).
- `core/`: Central configuration and database connection pooling.

### Frontend (`app/`)
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
cd fincore-backend
python -m pytest tests/ -v
```

---

## 🛡️ Future-Proof Design
- **Scalable DB**: Modular PostgreSQL schema with built-in Audit Logs and multi-tenant support (via `orgId`).
- **Dynamic OCR**: Easy to add support for new banks by simply updating the Regex Classifiers in `app/ocr/classifier.py`.
- **Hybrid Storage**: Seamlessly switch between local filesystem and AWS S3 via the `USE_LOCAL_STORAGE` flag.

---
**Vyrenzo Bank** — *Automating Financial Intelligence.*