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

export async function DELETE(request: NextRequest, context: any) {
    return handle(request, context, "DELETE");
}

async function handle(request: NextRequest, context: any, method: string) {
    // 1. In Next.js 16, params is a Promise
    const params = await context.params;
    const segments = params.path as string[];
    const path = segments.join("/");
    
    // 2. Discover Backend URL
    const vercelUrl = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
    let host = vercelUrl || "127.0.0.1:8000";
    const protocol = host.includes("127.0.0.1") || host.includes("localhost") ? "http" : "https";
    
    if (!host.includes("_/backend") && !host.includes("127.0.0.1")) {
        host = `${host}/_/backend`;
    }
    
    const url = new URL(request.url);
    // Remove duplicate v1 if already present in segments
    const cleanPath = path.startsWith("v1/") ? path : `v1/${path}`;
    const backendUrl = `${protocol}://${host}/api/${cleanPath}${url.search}`;

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
            options.body = await request.blob(); // Preserve binary/json data
        }

        const response = await fetch(backendUrl, options);
        
        if (!response.ok) {
            const text = await response.text().catch(() => "N/A");
            return NextResponse.json({ 
                error: `Backend ${response.status}`, 
                detail: text,
                target: backendUrl 
            }, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);

    } catch (err: any) {
        console.error(`[Proxy Error] ${backendUrl}:`, err.message);
        return NextResponse.json({ 
            error: "Backend Connectivity Failed", 
            message: err.message,
            target: backendUrl,
            hint: "Check if DATABASE_URL is set in Vercel settings."
        }, { status: 504 });
    }
}
