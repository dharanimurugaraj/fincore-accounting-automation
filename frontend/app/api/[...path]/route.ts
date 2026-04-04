/**
 * Smart Proxy that bridges the legacy frontend to the new modular FastAPI backend.
 * Handles:
 * - CamelCase (orgId) to snake_case (org_id) parameter conversion.
 * - Legacy legacy path mapping (documents -> uploads).
 * - Action-based routing for pipeline operations (confirm, approve).
 */

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  let path = params.path.join("/");
  const url = new URL(request.url);
  const searchParams = new URLSearchParams(url.search);

  // 1. Map legacy paths
  if (path === "documents") {
    path = "uploads";
  } else if (path === "pipeline/status") {
    // Convert /api/pipeline/status?runId=xxx -> /api/v1/pipeline/status/xxx
    const runId = searchParams.get("runId");
    if (runId) {
      path = `pipeline/status/${runId}`;
      searchParams.delete("runId");
    }
  }

  // 2. Convert common CamelCase parameters to snake_case
  if (searchParams.has("orgId")) {
    searchParams.set("org_id", searchParams.get("orgId")!);
    searchParams.delete("orgId");
  }
  if (searchParams.has("month")) {
    searchParams.set("statement_month", searchParams.get("month")!);
    searchParams.delete("month");
  }
  if (searchParams.has("runId")) {
    searchParams.set("run_id", searchParams.get("runId")!);
    searchParams.delete("runId");
  }

  const backendUrl = `${BACKEND_URL}/api/v1/${path}?${searchParams.toString()}`;

  try {
    const response = await fetch(backendUrl, {
      headers: {
        Authorization: request.headers.get("Authorization") || "",
        "Content-Type": "application/json",
      },
    });
    
    if (response.status === 404) {
      return NextResponse.json({ error: "Endpoint not found on backend" }, { status: 404 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`Proxy GET ${path} failed:`, error);
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  let path = params.path.join("/");
  const backendUrl = `${BACKEND_URL}/api/v1/${path}`;

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
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error(`Proxy POST ${path} failed:`, error);
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
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
