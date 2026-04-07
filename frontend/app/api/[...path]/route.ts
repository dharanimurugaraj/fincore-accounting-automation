import { NextRequest, NextResponse } from "next/server";

/**
 * Universal API Proxy Route (Next.js 16 Compatible)
 */

export const dynamic = "force-dynamic";

// Next.js 15/16: params is now a Promise
type RouteProps = {
    params: Promise<{ path: string[] }>;
};

export async function GET(request: NextRequest, props: RouteProps) {
    return handle(request, props.params);
}

export async function POST(request: NextRequest, props: RouteProps) {
    return handle(request, props.params);
}

export async function PUT(request: NextRequest, props: RouteProps) {
    return handle(request, props.params);
}

export async function PATCH(request: NextRequest, props: RouteProps) {
    return handle(request, props.params);
}

export async function DELETE(request: NextRequest, props: RouteProps) {
    return handle(request, props.params);
}

async function handle(request: NextRequest, paramsPromise: Promise<{ path: string[] }>) {
    const params = await paramsPromise;
    const segments = params.path || [];
    const path = segments.join("/") || "unresolved";
    const method = request.method;

    // 1. Determine the raw host string with multiple fallbacks
    let rawHost = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || "";
    const isLocal = process.env.NODE_ENV === "development";

    if (!rawHost) {
        if (isLocal) {
            rawHost = "http://localhost:8000";
        } else {
            const hostHeader = request.headers.get("host") || process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL || "localhost:8000";
            rawHost = hostHeader.includes("://") ? hostHeader : `https://${hostHeader}`;
        }
    }

    // 2. Parse Host accurately
    let protocol = "https";
    let cleanHost = "";

    try {
        const parsed = new URL(rawHost.startsWith("http") ? rawHost : `https://${rawHost}`);
        protocol = parsed.protocol.replace(":", "");
        cleanHost = (parsed.host + parsed.pathname).replace(/\/\/+/g, "/");
        if (cleanHost.endsWith("/")) cleanHost = cleanHost.slice(0, -1);
    } catch (e) {
        cleanHost = rawHost.replace(/^https?:\/\//, "").replace(/\/$/, "");
    }

    // 2.1 SAFETY: If cleanHost is still empty, force fallback to current domain
    if (!cleanHost || cleanHost === "/") {
        const fallback = request.headers.get("host") || process.env.VERCEL_PROJECT_PRODUCTION_URL || "finance.vyrenzo.in";
        cleanHost = fallback.replace(/^https?:\/\//, "");
    }

    // 3. Apply Vercel Multi-service Prefix if needed
    let finalHost = cleanHost;
    if (!isLocal && !cleanHost.includes("_/backend")) {
        finalHost = `${cleanHost}/_/backend`.replace(/\/\/+/g, "/");
    }
    // Final check for leading slash
    if (finalHost.startsWith("/")) finalHost = finalHost.slice(1);

    // 4. Construct Final Backend URL
    const url = new URL(request.url);
    const cleanPath = path.startsWith("v1/") ? path : `v1/${path}`;
    
    // Ensure no duplicate /api or /v1 segments
    let backendUrl = `${protocol}://${finalHost}`;
    if (!backendUrl.includes("/api")) {
        backendUrl += "/api";
    }
    backendUrl += `/${cleanPath}${url.search}`;
    // Fix any accidental triple slashes except after protocol
    backendUrl = backendUrl.replace(/([^:]\/)\/+/g, "$1");

    console.log(`[Proxy] ${method} -> ${backendUrl}`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 9500);

    try {
        const headers = new Headers(request.headers);
        const targetUrl = new URL(backendUrl);
        headers.set("host", targetUrl.host);
        
        if (method === "GET" || method === "DELETE" || method === "HEAD") {
            headers.delete("content-type");
        }

        const options: RequestInit = {
            method,
            headers: headers,
            cache: 'no-store',
            signal: controller.signal // Link the abort signal
        };

        if (method !== "GET" && method !== "HEAD") {
            try {
                options.body = await request.arrayBuffer();
            } catch (bodyErr) {
                console.error("[Proxy Body Error]", bodyErr);
            }
        }

        const response = await fetch(backendUrl, options);
        clearTimeout(timeoutId);

        console.log(`[Proxy Response] ${backendUrl} -> ${response.status} ${response.statusText}`);

        if (response.headers.get("content-type")?.includes("text/event-stream")) {
            return response;
        }

        const contentType = response.headers.get("content-type") || "";
        let responseData: any = null;

        if (contentType.includes("application/json")) {
            try {
                responseData = await response.json();
            } catch (e) {
                responseData = { error: "Failed to parse JSON" };
            }
        } else {
            const blob = await response.blob();
            return new Response(blob, {
                status: response.status,
                statusText: response.statusText,
                headers: response.headers
            });
        }

        if (!response.ok) {
            return NextResponse.json({ 
                error: responseData?.detail || responseData?.error || "Backend Error",
                status: response.status 
            }, { status: response.status });
        }

        return NextResponse.json(responseData);

    } catch (err: any) {
        clearTimeout(timeoutId);
        
        if (err.name === 'AbortError') {
            console.error(`[Proxy Timeout] Backend did not respond in 9.5s: ${backendUrl}`);
            return NextResponse.json({ 
                error: "Backend Dependency Timeout", 
                detail: "The Python backend took too long to respond. This is usually due to an unreachable database URL or a cold start.",
                url: backendUrl 
            }, { status: 504 });
        }

        return NextResponse.json({ 
            error: "Backend Connectivity Failed", 
            detail: err.message,
            url: backendUrl,
            debug: {
                rawHost: process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || "MISSING",
                finalHost: finalHost,
                isProduction: !isLocal
            }
        }, { status: 504 });
    }
}

