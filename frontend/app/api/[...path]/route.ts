/**
 * Universal Proxy for Next.js 16 - Handles all methods and segments.
 */
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, context: any) {
    return handle(request, context, "GET");
}

export async function POST(request: NextRequest, context: any) {
    return handle(request, context, "POST");
}

export async function PUT(request: NextRequest, context: any) {
    return handle(request, context, "PUT");
}

export async function PATCH(request: NextRequest, context: any) {
    return handle(request, context, "PATCH");
}

export async function DELETE(request: NextRequest, context: any) {
    return handle(request, context, "DELETE");
}

async function handle(request: NextRequest, context: any, method: string) {
    // 1. In Next.js 15, params is a Promise
    const params = await context.params || {};
    const segments = (params.path as string[]) || [];
    const path = segments.join("/") || "unresolved";

    
    // 2. Discover Backend URL — PRIORITIZE USER'S OVERRIDE & PORT
    const backendUrlEnv = process.env.BACKEND_URL;
    const isLocal = process.env.NODE_ENV === "development" || !process.env.VERCEL_URL;
    
    // In local dev, we want the default FastAPI port (8000). 
    // In Vercel production, we want to hit the mapped /_/backend prefix.
    let host = "";
    
    if (backendUrlEnv) {
        host = backendUrlEnv;
    } else if (isLocal) {
        host = "127.0.0.1:8000";
    } else {
        // Production Vercel: use current domain/hostname
        host = process.env.VERCEL_PROJECT_PRODUCTION_URL || request.headers.get("host") || process.env.VERCEL_URL || "127.0.0.1:8000";
    }

    // Auto-detect protocol
    const protocol = host.includes("127.0.0.1") || host.includes("localhost") || host.startsWith("http://") ? "http" : "https";
    
    // Clean up host (remove protocol if included in manual env, will prepend later)
    host = host.replace(/^https?:\/\//, "");

    // Append default routePrefix ONLY for production cloud hosting
    if (!host.includes("_/backend") && !isLocal) {
        host = `${host}/_/backend`;
    }

    
    const url = new URL(request.url);
    // Remove duplicate v1 if already present in segments
    const cleanPath = path.startsWith("v1/") ? path : `v1/${path}`;
    
    // Final constructed URL (ensuring we don't double /api if host already has it)
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

        const options: RequestInit = {
            method,
            headers: headers,
            cache: 'no-store'
        };

        if (method !== "GET" && method !== "HEAD") {
            try {
                options.body = await request.blob();
            } catch (bodyErr) {
                console.error("[Proxy Body Error]", bodyErr);
            }
        }

        const response = await fetch(backendUrl, options);
        
        // Handle Non-JSON responses gracefully (Vercel error pages)
        const contentType = response.headers.get("content-type") || "";
        let responseData: any;
        
        if (contentType.includes("application/json")) {
            responseData = await response.json().catch(() => null);
        }

        if (!response.ok) {
            const detailText = responseData ? JSON.stringify(responseData) : await response.text().catch(() => "N/A");
            console.error(`[Proxy Backend Error] ${response.status}:`, detailText.substring(0, 500));
            
            return NextResponse.json({ 
                error: `Backend ${response.status}`, 
                detail: detailText.substring(0, 1000), // Clip long HTML errors
                target: backendUrl 
            }, { status: response.status });
        }

        if (responseData) {
            return NextResponse.json(responseData);
        } else {
            // Fallback for non-JSON success?
            const textData = await response.text();
            return new NextResponse(textData, { 
                status: response.status,
                headers: { "Content-Type": contentType }
            });
        }

    } catch (err: any) {
        console.error(`[Proxy Critical Failure] ${backendUrl}:`, err.message);
        return NextResponse.json({ 
            error: "Backend Connectivity Failed", 
            message: err.message,
            target: backendUrl,
            hint: "Check environment variables and Vercel Multi-Project settings."
        }, { status: 504 });
    }

}
