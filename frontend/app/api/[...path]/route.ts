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

    let host = "";
    const backendUrlEnv = process.env.NEXT_PUBLIC_BACKEND_URL;
    const isLocal = process.env.NODE_ENV === "development";
    
    if (backendUrlEnv) {
        host = backendUrlEnv;
    } else if (isLocal) {
        host = "localhost:8000";
    } else {
        host = process.env.VERCEL_PROJECT_PRODUCTION_URL || request.headers.get("host") || process.env.VERCEL_URL || "localhost:8000";
    }

    const protocol = host.includes("127.0.0.1") || host.includes("localhost") || host.startsWith("http://") ? "http" : "https";
    host = host.replace(/^https?:\/\//, "");

    if (!host.includes("_/backend") && !isLocal) {
        host = `${host}/_/backend`;
    }

    const url = new URL(request.url);
    const cleanPath = path.startsWith("v1/") ? path : `v1/${path}`;
    
    let backendUrl = "";
    if (host.includes("/api")) {
        backendUrl = `${protocol}://${host}/${cleanPath}${url.search}`;
    } else {
        backendUrl = `${protocol}://${host}/api/${cleanPath}${url.search}`;
    }

    console.log(`[Proxy] ${method} -> ${backendUrl}`);

    try {
        const headers = new Headers(request.headers);
        headers.set("host", new URL(backendUrl).host);
        
        if (method === "GET" || method === "DELETE" || method === "HEAD") {
            headers.delete("content-type");
        }

        const options: RequestInit = {
            method,
            headers: headers,
            cache: 'no-store'
        };

        if (method !== "GET" && method !== "HEAD") {
            try {
                options.body = await request.arrayBuffer();
            } catch (bodyErr) {
                console.error("[Proxy Body Error]", bodyErr);
            }
        }

        const response = await fetch(backendUrl, options);
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
        console.error(`[Proxy Failure] ${backendUrl}:`, err.message);
        
        if (backendUrl.includes("localhost")) {
            try {
                const altUrl = backendUrl.replace("localhost", "127.0.0.1");
                console.log(`[Proxy Fallback] Trying ${altUrl}...`);
                const altRes = await fetch(altUrl, { method, headers: request.headers });
                if (altRes.ok) return altRes;
            } catch (e2) {}
        }

        return NextResponse.json({ 
            error: "Backend Connectivity Failed", 
            detail: err.message,
            url: backendUrl 
        }, { status: 504 });
    }
}
