# Vyrenzo Bank — Environment Variables Documentation

This document describes all environment variables used by the Vyrenzo Bank application.

---

## ⚙️ Backend Environment Variables (`backend/.env`)

These must be defined in the `backend/.env` file for local development or configured as Environment Variables in the backend runtime for production deployments.

### 1. Database Configuration
*   **`DATABASE_URL`**
    *   **Description**: Complete connection URI for the PostgreSQL 16+ instance.
    *   **Default (Local)**: `postgresql://fincore:fincore_dev@localhost:5432/fincore_dev`
    *   **Required**: Yes (both local and production)

*   **`PG_ADMIN_USER`**
    *   **Description**: Superuser username used during migration scripts or DB initialization.
    *   **Default**: `postgres`
    *   **Required**: No

*   **`PG_ADMIN_PASSWORD`**
    *   **Description**: Superuser password for database initialization.
    *   **Default**: `""`
    *   **Required**: No

### 2. Storage Adapter Configuration
*   **`USE_LOCAL_STORAGE`**
    *   **Description**: Toggle switch between local directory storage and AWS S3 storage.
    *   **Default**: `true`
    *   **Values**: `true` (use local file system), `false` (use AWS S3)
    *   **Required**: Yes

*   **`LOCAL_STORAGE_PATH`**
    *   **Description**: Relative path to the folder where statements are kept when `USE_LOCAL_STORAGE` is `true`.
    *   **Default**: `./storage/data`
    *   **Required**: Yes, if `USE_LOCAL_STORAGE=true`

*   **`S3_BUCKET`**
    *   **Description**: Name of the target AWS S3 bucket.
    *   **Required**: Yes, if `USE_LOCAL_STORAGE=false`

*   **`S3_REGION`**
    *   **Description**: Region code of the bucket.
    *   **Default**: `ap-south-1`
    *   **Required**: Yes, if `USE_LOCAL_STORAGE=false`

*   **`AWS_ACCESS_KEY_ID`**
    *   **Description**: AWS IAM user access key.
    *   **Required**: Yes, if `USE_LOCAL_STORAGE=false`

*   **`AWS_SECRET_ACCESS_KEY`**
    *   **Description**: AWS IAM user secret key.
    *   **Required**: Yes, if `USE_LOCAL_STORAGE=false`

### 3. AI / LLM Configuration
*   **`GEMINI_API_KEY`**
    *   **Description**: API key obtained from Google AI Studio to run OCR classification tasks.
    *   **Required**: Yes (both local and production)

*   **`OPENROUTER_API_KEY`**
    *   **Description**: API Key to execute LLM calls via OpenRouter API (as fallback).
    *   **Required**: No

*   **`OPENROUTER_MODEL`**
    *   **Description**: Fallback model key.
    *   **Default**: `google/gemini-2.5-flash-lite`
    *   **Required**: No

### 4. Firebase Authentication (Admin SDK)
*   **`FIREBASE_PROJECT_ID`**
    *   **Description**: Project ID associated with the Firebase console.
    *   **Required**: Yes

*   **`FIREBASE_SERVICE_ACCOUNT`**
    *   **Description**: JSON string of your Firebase service account private key credentials.
    *   **Required**: Yes (must be minified/flattened as single line string in production env)

### 5. Services & Integrations
*   **`FRONTEND_URL`**
    *   **Description**: The base origin URL of the Next.js frontend. Used for CORS verification.
    *   **Default**: `http://localhost:3000`
    *   **Required**: Yes

*   **`USE_RATE_FIXTURES`**
    *   **Description**: If true, uses pre-configured static rate datasets for Forex average and high calculations rather than hitting external API services.
    *   **Default**: `true`
    *   **Required**: Yes

*   **`RESEND_API_KEY`**
    *   **Description**: Resend API key for administrative alerts and email updates.
    *   **Required**: No

---

## 🖥️ Frontend Environment Variables (`frontend/.env.local`)

These must be defined in the `frontend/.env.local` file for local development or configured on Vercel for the frontend service.

### 1. API Route Configs
*   **`NEXT_PUBLIC_BACKEND_URL`** or **`BACKEND_URL`**
    *   **Description**: URL to route API calls to the FastAPI backend.
    *   **Default (Local)**: `http://127.0.0.1:8000`
    *   **Default (Production Vercel)**: `/_/backend` (Relative path handles the multi-project routing)
    *   **Required**: Yes

### 2. Client Firebase SDK Configs
*   **`NEXT_PUBLIC_FIREBASE_API_KEY`**
    *   **Description**: Public web API key.
    *   **Required**: Yes

*   **`NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`**
    *   **Description**: Firebase authentication domain host (e.g. `vyrenzo-auth.firebaseapp.com`).
    *   **Required**: Yes

*   **`NEXT_PUBLIC_FIREBASE_PROJECT_ID`**
    *   **Description**: Firebase project identifier.
    *   **Required**: Yes

*   **`NEXT_PUBLIC_FIREBASE_APP_ID`**
    *   **Description**: Public client app identification string.
    *   **Required**: Yes

### 3. Production Authentication Gate
*   **`AUTH_USER`**
    *   **Description**: The basic authentication username gate for the live `/login` screen in production.
    *   **Default**: `vyrenzo`
    *   **Required**: No

*   **`AUTH_PASS`**
    *   **Description**: The basic authentication password gate for the live `/login` screen in production.
    *   **Default**: `finance@1234`
    *   **Required**: No

### 4. Optional Frontend S3 Access
*   **`AWS_REGION`** (Default: `ap-south-1`)
*   **`AWS_ACCESS_KEY_ID`**
*   **`AWS_SECRET_ACCESS_KEY`**
*   **`S3_BUCKET_NAME`** (Default: `fincore-documents-dev`)
