/**
 * Smart Proxy that bridges the legacy frontend to the new modular FastAPI backend.
 * Handles:
 * - CamelCase (orgId) to snake_case (org_id) parameter conversion.
 * - Legacy legacy path mapping (documents -> uploads).
 * - Action-based routing for pipeline operations (confirm, approve).
 */

import { NextRequest, NextResponse } from "next/server";

// Auto-detect backend URL based on environment
const getBackendUrl = () => {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL;
  
  // Local development fallback
  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:8000";
  }
  
  // Vercel Production — using the experimentalServices routePrefix
  // We use VERCEL_PROJECT_PRODUCTION_URL if available, or fallback to relative routing if possible (though fetch needs absolute)
  const vercelUrl = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
  if (vercelUrl) {
    return `https://${vercelUrl}/_/backend`;
  }
  
  return "http://127.0.0.1:8000";
};

const BACKEND_URL = getBackendUrl();

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await params;
  let path = segments.join("/");
  
  const url = new URL(request.url);
  const searchParams = new URLSearchParams(url.search);

  // 1. Map legacy paths
  if (path === "documents") {
    path = "uploads";
  } else if (path === "pipeline/status") {
    const runId = searchParams.get("runId");
    if (runId) {
      path = `pipeline/status/${runId}`;
      searchParams.delete("runId");
    }
  }

  // 2. Normalize parameters to snake_case for the Python backend
  if (searchParams.has("orgId")) {
    searchParams.set("org_id", searchParams.get("orgId")!);
    searchParams.delete("orgId");
  }
  if (searchParams.has("month")) {
    searchParams.set("statement_month", searchParams.get("month")!);
    searchParams.delete("month");
  }

  const backendUrl = `${BACKEND_URL}/api/v1/${path}${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  try {
    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Authorization": request.headers.get("Authorization") || "",
        "Content-Type": "application/json",
      },
      next: { revalidate: 0 },
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown error");
      console.error(`Backend error [${response.status}] at ${path}:`, errorText);
      
      return NextResponse.json({ 
        error: `Backend error ${response.status}`,
        detail: errorText,
        path: path
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error(`Proxy failure connecting to ${backendUrl}:`, error.message);
    return NextResponse.json({ 
      error: "Backend Connection Failed",
      message: error.message,
      target: backendUrl,
      hint: "Ensure BACKEND_URL is correctly set in your environment."
    }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params;
  let path = pathSegments.join("/");
  const contentType = request.headers.get("content-type") || "";

  // 0. Handle multi-part form data (uploads)
  if (contentType.includes("multipart/form-data")) {
    const backendUrl = `${BACKEND_URL}/api/v1/${path}`;
    try {
      const formData = await request.formData();
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          Authorization: request.headers.get("Authorization") || "",
        },
        body: formData,
      });
      if (!response.ok) {
        const text = await response.text().catch(() => "Upload failed");
        return NextResponse.json({ error: text }, { status: response.status });
      }
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    } catch (error) {
      console.error(`Proxy POST ${path} (multipart) failed:`, error);
      return NextResponse.json({ error: "Upload failed" }, { status: 502 });
    }
  }

  try {
    const body = await request.json();
    
    // 3. Convert CamelCase keys in POST body to snake_case
    const snakeBody: any = {};
    for (const [key, val] of Object.entries(body)) {
      const snakeKey = key.replace(/([A-Z])/g, "_$1").toLowerCase();
      snakeBody[snakeKey] = val;
    }

    // 4. Map legacy actions
    if (path === "pipeline") {
      if (body.action === "confirm") {
        return _forward(request, `${BACKEND_URL}/api/v1/pipeline/confirm`, {
          run_id: body.run_id || body.runId,
        });
      }
      if (body.action === "approve") {
        return _forward(request, `${BACKEND_URL}/api/v1/pipeline/approve`, {
          run_id: body.run_id || body.runId,
          user_id: body.user_id || body.userId,
        });
      }
      if (!path.endsWith("/run")) {
        path = "pipeline/run";
      }
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/${path}`, {
      method: "POST",
      headers: {
        Authorization: request.headers.get("Authorization") || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(snakeBody),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "Backend error");
      return NextResponse.json({ error: text }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`Proxy POST ${path} failed to reach ${BACKEND_URL}/api/v1/${path}:`, error);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

async function _forward(req: NextRequest, url: string, body: any) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: req.headers.get("Authorization") || "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "Forward failed");
    return NextResponse.json({ error: text }, { status: response.status });
  }
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
