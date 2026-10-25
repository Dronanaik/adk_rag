import type {
  ApiErrorEnvelope,
  AppRole,
  DocumentSummary,
  GraphNodeItem,
  HealthResponse,
  MemoryFactItem,
  MemoryUpdatePayload,
  PaginationMeta,
  SessionSummary,
  SubgraphResponseData,
} from "../types/api";

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

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

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

export async function fetchSessions(): Promise<{
  data: SessionSummary[];
  pagination?: PaginationMeta;
}> {
  return apiRequest<{ data: SessionSummary[]; pagination?: PaginationMeta }>(
    "/api/v1/sessions",
  );
}

export async function createSession(title: string): Promise<{ data: SessionSummary }> {
  return apiRequest<{ data: SessionSummary }>("/api/v1/sessions", {
    method: "POST",
    body: { title },
  });
}

export async function fetchDocuments(params?: {
  status?: string;
  search?: string;
}): Promise<{ data: DocumentSummary[]; pagination?: PaginationMeta }> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== "ALL") {
    query.set("status", params.status);
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<{ data: DocumentSummary[]; pagination?: PaginationMeta }>(
    `/api/v1/documents${suffix}`,
  );
}

export async function uploadDocumentFile(
  file: File,
  title: string,
  adminApiKey: string,
): Promise<{ data: DocumentSummary }> {
  const formData = new FormData();
  formData.append("file", file);
  if (title.trim()) {
    formData.append("title", title.trim());
  }
  return apiRequest<{ data: DocumentSummary }>("/api/v1/documents", {
    method: "POST",
    body: formData,
    role: "admin",
    adminApiKey,
  });
}

export async function reprocessDocumentById(
  documentId: string,
  adminApiKey: string,
): Promise<{ data: DocumentSummary }> {
  return apiRequest<{ data: DocumentSummary }>(
    `/api/v1/documents/${documentId}/reprocess`,
    {
      method: "POST",
      role: "admin",
      adminApiKey,
    },
  );
}

export async function deleteDocumentById(
  documentId: string,
  adminApiKey: string,
): Promise<void> {
  await apiRequest<Record<string, unknown>>(`/api/v1/documents/${documentId}`, {
    method: "DELETE",
    role: "admin",
    adminApiKey,
  });
}

export async function fetchGraphEntities(params?: {
  entityType?: string;
  search?: string;
}): Promise<{ data: GraphNodeItem[]; pagination?: PaginationMeta }> {
  const query = new URLSearchParams();
  if (params?.entityType && params.entityType !== "ALL") {
    query.set("entity_type", params.entityType);
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<{ data: GraphNodeItem[]; pagination?: PaginationMeta }>(
    `/api/v1/kg/entities${suffix}`,
  );
}

export async function fetchEntitySubgraph(
  entityId: string,
  maxHops: number,
): Promise<{ data: SubgraphResponseData }> {
  return apiRequest<{ data: SubgraphResponseData }>(
    `/api/v1/kg/entities/${entityId}/subgraph?max_hops=${String(maxHops)}`,
  );
}

export async function fetchMemories(params?: {
  memoryTier?: string;
  search?: string;
}): Promise<{ data: MemoryFactItem[]; pagination?: PaginationMeta }> {
  const query = new URLSearchParams();
  if (params?.memoryTier && params.memoryTier !== "ALL") {
    query.set("memory_tier", params.memoryTier);
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest<{ data: MemoryFactItem[]; pagination?: PaginationMeta }>(
    `/api/v1/memories${suffix}`,
  );
}

export async function updateMemoryById(
  memoryId: string,
  payload: MemoryUpdatePayload,
  adminApiKey: string,
): Promise<{ data: MemoryFactItem }> {
  return apiRequest<{ data: MemoryFactItem }>(`/api/v1/memories/${memoryId}`, {
    method: "PATCH",
    body: payload,
    role: "admin",
    adminApiKey,
  });
}

export async function deleteMemoryById(
  memoryId: string,
  adminApiKey: string,
): Promise<void> {
  await apiRequest<Record<string, unknown>>(`/api/v1/memories/${memoryId}`, {
    method: "DELETE",
    role: "admin",
    adminApiKey,
  });
}
