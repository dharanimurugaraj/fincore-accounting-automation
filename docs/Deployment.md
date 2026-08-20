# Vyrenzo Bank — Deployment Documentation

Vyrenzo Bank is configured for high-performance hosting on **Vercel** as a multi-service monorepo. It runs the frontend Next.js application alongside the Python FastAPI backend on a single domain.

---

## ⚡ Vercel Multi-Service Configuration

The repository uses the Vercel Multi-Service feature configured via [vercel.json](file:///d:/Vyrenzo%20Fintool%20June/vyrenzo-proj1-fincore/vercel.json) in the workspace root:

```json
{
    "experimentalServices": {
        "frontend": {
            "entrypoint": "frontend",
            "routePrefix": "/",
            "framework": "nextjs"
        },
        "backend": {
            "entrypoint": "backend",
            "routePrefix": "/_/backend"
        }
    }
}
```

### 🛣️ Routing Mechanics
*   Any request to `/` or standard paths is routed to the **Next.js** build in the `frontend/` directory.
*   Any request to `/_/backend` is automatically routed to the **FastAPI** server built in the `backend/` directory.
*   The Next.js app communicates with the backend via its [Smart Proxy Gateway](file:///d:/Vyrenzo%20Fintool%20June/vyrenzo-proj1-fincore/frontend/app/api/%5B...path%5D/route.ts) which targets `/_/backend` under the hood.

---

## 🚀 Step-by-Step Production Deployment

### 1. Database Setup in Production
Before deploying the code, set up your production PostgreSQL instance (e.g. via AWS RDS, Neon, or Supabase).
1.  Obtain your production connection string:
    `postgresql://<user>:<password>@<host>:<port>/<db>?sslmode=require`
2.  Import the schema script:
    `psql -d <prod-db-url> -f backend/database/schema.sql`

### 2. Seeding Production Roles & Default Entities
To seed standard roles (`SUPER_ADMIN`, `ADMIN`, `ANALYST`, etc.) and the default organization (`Vyrenzo Bank Demo`), edit the database URL inside [sync_prod.py](file:///d:/Vyrenzo%20Fintool%20June/vyrenzo-proj1-fincore/sync_prod.py) and execute it:
```powershell
python sync_prod.py
```

### 3. Vercel Project Creation
1.  Go to the **Vercel Dashboard** and click **Add New Project**.
2.  Import the GitHub repository: `vyrenzo-proj1-fincore`.
3.  Vercel will auto-detect the root `vercel.json` and split the project deployment configuration into two separate environments (Frontend and Backend services).

### 4. Configure Production Environment Variables
On Vercel, navigate to settings and add the environment variables for both services:

#### 🖥️ Frontend Service Variables
*   `BACKEND_URL`: `/_/backend` (Relative routing is handled automatically by the Smart Proxy).
*   `AUTH_USER`: Admin basic-auth username (Default: `vyrenzo`).
*   `AUTH_PASS`: Admin basic-auth password (Default: `finance@1234`).
*   *Add any client-side Firebase Configuration keys (e.g., `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` etc.).*

#### ⚙️ Backend Service Variables
*   `DATABASE_URL`: Connection string pointing to the production Postgres database.
*   `GEMINI_API_KEY`: API Key obtained from Google AI Studio.
*   `USE_LOCAL_STORAGE`: `false` (forces AWS S3 upload mode instead of local disk storage).
*   `S3_BUCKET`: Name of your AWS S3 bucket.
*   `S3_REGION`: Region code of the bucket (e.g. `ap-south-1`).
*   `AWS_ACCESS_KEY_ID`: AWS IAM user access key.
*   `AWS_SECRET_ACCESS_KEY`: AWS IAM user secret access key.
*   `FIREBASE_PROJECT_ID`: The ID of your Firebase project.
*   `FIREBASE_SERVICE_ACCOUNT`: The Firebase Admin JSON certificate payload (stringified).

---

## 🛠️ Local Development Server Deployment

To simulate the system locally, run the multi-process setup from the root directory:

1.  Make sure Node.js dependencies are installed (`npm install` in both root and `frontend/`).
2.  Make sure Python dependencies are installed (`pip install -r backend/requirements.txt`).
3.  Run the start script:
    ```bash
    npm run dev
    ```
4.  This spawns:
    *   **Frontend**: Next.js running on [http://localhost:3000](http://localhost:3000)
    *   **Backend**: FastAPI running on [http://localhost:8000](http://localhost:8000)
