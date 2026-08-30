import { NextRequest, NextResponse } from "next/server";

/**
 * Universal API Proxy Route (Next.js 16 Compatible)
 */

export const dynamic = "force-dynamic";
export const maxDuration = 300; // Allow up to 300s (Vercel Pro max) for long-running pipeline jobs

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
        rawHost = isLocal ? "http://127.0.0.1:8000" : (process.env.VERCEL_URL || "finance.vyrenzo.in");
    }

    // 2. Parse Host accurately
    let protocol = "https";
    let cleanHost = "";

    try {
        // Fix for "/_/backend" style relative URLs
        const hostToParse = rawHost.startsWith("/") ? `https://${request.headers.get("host")}${rawHost}` : rawHost;
        const parsed = new URL(hostToParse.startsWith("http") ? hostToParse : `https://${hostToParse}`);
        
        protocol = parsed.protocol.replace(":", "");
        cleanHost = (parsed.host + parsed.pathname).replace(/\/\/+/g, "/");
        if (cleanHost.endsWith("/")) cleanHost = cleanHost.slice(0, -1);
    } catch (e) {
        cleanHost = rawHost.replace(/^https?:\/\//, "").replace(/\/$/, "");
    }

    // 2.1 SAFETY: Ensure cleanHost does not collapse to "_"
    if (!cleanHost || cleanHost === "_" || cleanHost === "/") {
        cleanHost = request.headers.get("host") || "finance.vyrenzo.in";
    }

    // 3. Removed legacy /_/backend prefix logic
    let finalHost = cleanHost;
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

    // Allow up to 295s in production (just under the 300s Vercel Pro maxDuration),
    // and 60s locally. This prevents cold-start and long-running pipeline timeouts.
    const timeoutLimit = !isLocal ? 295000 : 60000;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutLimit);

    try {
        const headers = new Headers(request.headers);
        // Remove headers that might interfere with the backend or are forbidden
        headers.delete("host");
        headers.delete("connection");
        headers.delete("keep-alive");
        
        const targetUrl = new URL(backendUrl);
        
        if (method === "GET" || method === "DELETE" || method === "HEAD") {
            headers.delete("content-type");
        }

        const options: RequestInit = {
            method,
            headers: headers,
            cache: 'no-store',
            signal: controller.signal, // Link the abort signal
            redirect: 'manual' // Pass redirects (like 307 to R2) back to the client
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

        // Return standard response or redirect
        if (response.status >= 300 && response.status < 400) {
            return new Response(null, {
                status: response.status,
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
            console.error(`[Proxy Timeout] Backend did not respond in ${timeoutLimit/1000}s: ${backendUrl}`);
            return NextResponse.json({ 
                error: "Backend Dependency Timeout", 
                detail: "The Python backend (or database) took too long to respond. This is common with 'cold starts' or unreachable databases. Ensure your DATABASE_URL is configured correctly in the Vercel Dashboard.",
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

