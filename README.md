# FinCore: AI-Powered Financial Intelligence Platform

FinCore (formerly Vyrenzo Bank) is a next-generation banking intelligence platform designed to automate the extraction, analysis, and reconciliation of complex financial data. Built for accounting professionals and financial analysts, it transforms unstructured bank statements into verified, computation-ready insights.

---

## 🚀 The Problem & Solution

**The Problem:** Financial analysts spend countless hours manually extracting transactional data from diverse, unstructured PDF bank statements to reconcile Working Capital Demand Loans (WCDL), Cash Credit (CC) interest, and Forex excess. This manual process is highly prone to human error and scaling bottlenecks.

**The Solution:** FinCore leverages an intelligent, multi-stage pipeline using Large Language Models (Gemini 2.5 Flash Lite) and a deterministic Python computation engine to automatically classify documents, extract transaction data with high-confidence OCR, and generate automated Working Sheets and Management Reports.

---

## ✨ Key Capabilities

- **Intelligent Document Extraction**: Recognizes bank-specific PDF formats, classifies accounts, and extracts transactional data with high-confidence OCR using Gemini 2.5 Flash Lite.
- **Automated Financial Reconciliation**: Processes raw data through a verified, deterministic formula engine to reconcile:
  - Cash Credit (CC) Interest
  - WCDL Interest Calculation
  - ROI Deviation Analysis
  - Forex Rate Verification
  - Limit Utilisation Checks
- **Automated Reporting**: Generates comprehensive Working Sheets and Management Reports in standardized Excel formats.
- **Secure Multi-Tenant Architecture**: Full auth-gated dashboard with role-based access control (RBAC), multi-tenant organization support, and audit logging.

---

## 🏗️ Architecture & Technology Stack

FinCore utilizes a modern, split-stack Monorepo architecture designed for modularity, security, and scalability.

### Technology Stack
| Layer | Technology |
|---|---|
| **Frontend UI** | Next.js 16 (App Router), Tailwind CSS, React |
| **Backend API** | Python, FastAPI |
| **Database** | PostgreSQL 16 (psycopg2) |
| **AI/OCR Engine** | Google Gemini 2.5 Flash Lite |
| **Authentication** | Firebase Auth (ID Tokens) |

### High-Level Architecture

- **The Frontend (UI & Gateway)**: A responsive, React-based dashboard that visualizes real-time pipeline progress. It includes a **Smart Proxy** (Next.js middleware) that routes frontend API requests to the Python backend while preserving authentication headers and providing a consistent API boundary between the frontend and backend.
- **The Backend (Computation & Pipeline)**: A FastAPI service that manages a discrete 3-stage graph-based pipeline (Extraction -> Computation -> Reporting). It uses a pure-Python, zero-dependency formula engine for critical financial calculations, ensuring maximum testability and accuracy.
- **Data & Storage**: Backed by a PostgreSQL schema utilizing UUIDs, Enums for state management, and strict relational constraints. Storage is abstracted behind a provider interface, supporting local storage and S3-compatible object storage.

---

## 🧠 Key Engineering Decisions

- **Deterministic Computation Engine**: Separated the LLM extraction logic from the mathematical computation. The LLM handles unstructured data extraction, while a pure Python engine executes deterministic financial formulas, providing deterministic and reproducible financial calculations.
- **API Proxy Layer:** Added a Next.js API proxy to provide a consistent frontend API boundary and route requests to the FastAPI backend without coupling the client directly to backend URL details.
- **Extensible OCR Classifiers**: Designed the extraction service to easily support new banking formats by simply updating Regex-based classifiers without altering the core pipeline.
- **Secure Authentication Flow**: Utilizes Firebase Auth for seamless SSO/login, while strictly mapping Firebase UID tokens to internal PostgreSQL `User` records. Fallback mapping via email ensures seamless onboarding and prevents unique constraint violations during migration.

---

## 📍 Product Status & Roadmap

**Current Status (Implemented):**
- ✅ Secure User Authentication & RBAC setup.
- ✅ Next.js Dashboard UI with pipeline monitoring.
- ✅ 3-Stage Pipeline (OCR, Computation, Reporting).
- ✅ PostgreSQL database schema and connection pooling.
- ✅ Excel Report Generation for Working Sheets.

**Roadmap (Planned):**
- ⏳ Direct integration with open banking APIs for automated data fetching.
- ⏳ Advanced anomaly detection for fraudulent transactions.
- ⏳ Real-time collaborative document annotation.
- ⏳ Comprehensive multi-currency Forex reconciliations.

---

## 👨‍💻 My Contribution

My work on FinCore has focused on frontend–backend integration, authentication, production infrastructure, and database reliability.
- **Authentication & Security Hardening**: Architected the backend security layer (`app/core/security.py`) to seamlessly map Firebase Auth tokens to PostgreSQL users, handling edge cases like duplicate email constraints and mapping legacy accounts.
- **Infrastructure & Routing**: Streamlined the production routing by removing legacy proxies and resolving deployment configurations. Disabled unnecessary HTTP Basic Auth middleware that interrupted the user experience.
- **Database & Architecture Auditing**: Maintained and verified the integrity of the PostgreSQL schema, ensuring strict relationships for organizations, users, and pipeline runs.

<!-- Placeholder for product screenshots -->
<!-- ![Dashboard Overview](./docs/screenshots/dashboard.png) -->
<!-- ![Pipeline Monitoring](./docs/screenshots/pipeline.png) -->