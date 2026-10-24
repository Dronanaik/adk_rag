import type { ApiErrorEnvelope, AppRole, HealthResponse } from "../types/api";

export interface RequestClientOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  role?: AppRole;
  adminApiKey?: string;
  signal?: AbortSignal;
}

export class ApiClientError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly requestId: string;

  constructor(statusCode: number, code: string, message: string, requestId: string) {
    super(message);
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.code = code;
    this.requestId = requestId;
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export async function apiRequest<TResponse>(
  path: string,
  options: RequestClientOptions = {},
): Promise<TResponse> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-App-Role": options.role ?? "researcher",
  };

  if (options.adminApiKey) {
    headers["X-Admin-Api-Key"] = options.adminApiKey;
  }

  let serializedBody: BodyInit | undefined;
  if (options.body instanceof FormData) {
    serializedBody = options.body;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    serializedBody = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: serializedBody,
    signal: options.signal,
  });

  if (!response.ok) {
    const fallbackReqId = response.headers.get("X-Request-Id") ?? "req_unknown";
    try {
      const errJson = (await response.json()) as ApiErrorEnvelope;
      throw new ApiClientError(
        response.status,
        errJson.error.code,
        errJson.error.message,
        errJson.error.request_id,
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        throw err;
      }
      throw new ApiClientError(
        response.status,
        "HTTP_ERROR",
        `Request failed with status ${String(response.status)}`,
        fallbackReqId,
      );
    }
  }

  return (await response.json()) as TResponse;
}

export async function fetchSystemHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/api/v1/health");
}

