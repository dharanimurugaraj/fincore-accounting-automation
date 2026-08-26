/**
 * Smart API client for FinCore.
 * Automatically attaches the Firebase idToken from localStorage for EVERY request.
 */

const isDevelopment = process.env.NODE_ENV === "development";
export const API_BASE = isDevelopment ? "/api/v1" : "/_/backend/api/v1";

interface RequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
  asFormData?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {}, asFormData = false } = options;

  // 1. Always pull latest token from localStorage
  // The AuthProvider keeps this refreshed
  const token = typeof window !== "undefined" ? localStorage.getItem("fincore_token") : null;

  const requestHeaders: Record<string, string> = {
    ...headers,
  };

  if (token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  if (!asFormData) {
    requestHeaders["Content-Type"] = "application/json";
  }

  // Ensure path doesn't have leading / if API_BASE has trailing / or vice versa
  const cleanPath = path.startsWith("/") ? path.substring(1) : path;
  const url = `${API_BASE}/${cleanPath}`;

  const fetchOptions: RequestInit = {
    method,
    headers: requestHeaders,
    body: asFormData ? (body as FormData) : (body ? JSON.stringify(body) : undefined),
  };

  try {
    const response = await fetch(url, fetchOptions);
    
    if (response.status === 401) {
      console.error("Auth Fail: Session expired or invalid.");
      // Option: Trigger logout globally
    } else if (response.status === 403) {
      console.error("Auth Fail: Permission denied.");
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.error || `Request failed with status ${response.status}`);
    }

    return response.json();
  } catch (err: any) {
    console.error(`API Call [${method}] ${path} failed:`, err.message);
    throw err;
  }
}

export const api = {
  get: <T>(path: string, headers?: Record<string, string>) => 
    apiRequest<T>(path, { method: "GET", headers }),
    
  post: <T>(path: string, body: any, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "POST", body, headers }),
    
  postForm: <T>(path: string, formData: FormData, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "POST", body: formData, headers, asFormData: true }),
    
  patch: <T>(path: string, body: any, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "PATCH", body, headers }),
    
  delete: <T>(path: string, headers?: Record<string, string>) =>
    apiRequest<T>(path, { method: "DELETE", headers }),
};
