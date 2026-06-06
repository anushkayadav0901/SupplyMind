// frontend/lib/api.ts
// Centralized API client for SupplyMind backend.

import type {
  AnalyticsOverview,
  DocumentAnalytics,
  DocumentListItem,
  Document,
  ExtractionSummary,
  HealthResponse,
  RagAnswer,
  RagIndexResponse,
  RagIndexedDocuments,
  RagStatus,
  RiskDistribution,
  RiskSummary,
  SpendSummary,
  TopVendorsResponse,
  UploadResponse,
  VendorAnalytics,
  VendorDetail,
  VendorListItem,
} from "./types";

const DEFAULT_API_BASE = "http://127.0.0.1:8000/api/v1";

export const API_BASE_URL = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_URL);

function normalizeApiBaseUrl(value: string | undefined): string {
  const rawValue = value?.trim() || DEFAULT_API_BASE;
  const withoutTrailingSlash = rawValue.replace(/\/+$/, "");

  try {
    const parsed = new URL(withoutTrailingSlash);

    if (parsed.pathname === "" || parsed.pathname === "/") {
      parsed.pathname = "/api/v1";
      return parsed.toString().replace(/\/+$/, "");
    }
  } catch {
    return withoutTrailingSlash;
  }

  return withoutTrailingSlash;
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    const body = await response.json().catch(() => null);

    if (typeof body?.detail === "string") {
      return body.detail;
    }

    if (typeof body?.message === "string") {
      return body.message;
    }
  }

  const text = await response.text().catch(() => "");
  return text || response.statusText || `Request failed with status ${response.status}`;
}

function createNetworkErrorMessage(url: string): string {
  return [
    `SupplyMind backend is unreachable at ${url}.`,
    "Start the FastAPI server on port 8000 or set NEXT_PUBLIC_API_URL to the backend API base URL.",
  ].join(" ");
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = normalizeApiBaseUrl(baseUrl);
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    let response: Response;

    try {
      response = await fetch(url, {
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
        ...options,
      });
    } catch {
      throw new ApiRequestError(createNetworkErrorMessage(url), 0, url);
    }

    if (!response.ok) {
      throw new ApiRequestError(await readErrorMessage(response), response.status, url);
    }

    return response.json() as Promise<T>;
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  async listDocuments(
    skip = 0,
    limit = 50
  ): Promise<DocumentListItem[]> {
    return this.request<DocumentListItem[]>(
      `/documents?skip=${skip}&limit=${limit}`
    );
  }

  async getDocumentById(id: number): Promise<Document> {
    return this.request<Document>(`/documents/${id}`);
  }

  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${this.baseUrl}/documents/upload`;
    let response: Response;

    try {
      response = await fetch(url, {
        method: "POST",
        body: formData,
      });
    } catch {
      throw new ApiRequestError(createNetworkErrorMessage(url), 0, url);
    }

    if (!response.ok) {
      throw new ApiRequestError(await readErrorMessage(response), response.status, url);
    }

    return response.json() as Promise<UploadResponse>;
  }

  async listVendors(
    skip = 0,
    limit = 50
  ): Promise<VendorListItem[]> {
    return this.request<VendorListItem[]>(
      `/vendors?skip=${skip}&limit=${limit}`
    );
  }

  async getVendorById(id: number): Promise<VendorDetail> {
    return this.request<VendorDetail>(`/vendors/${id}`);
  }

  async getRiskSummary(): Promise<RiskSummary> {
    return this.request<RiskSummary>("/vendors/risk-summary");
  }

  async getOverviewAnalytics(): Promise<AnalyticsOverview> {
    return this.request<AnalyticsOverview>("/analytics/overview");
  }

  async getDocumentAnalytics(): Promise<DocumentAnalytics> {
    return this.request<DocumentAnalytics>("/analytics/documents");
  }

  async getVendorAnalytics(): Promise<VendorAnalytics> {
    return this.request<VendorAnalytics>("/analytics/vendors");
  }

  async getRiskDistribution(): Promise<RiskDistribution> {
    return this.request<RiskDistribution>("/analytics/risk-distribution");
  }

  async getSpendSummary(): Promise<SpendSummary> {
    return this.request<SpendSummary>("/analytics/spend-summary");
  }

  async getTopVendors(limit = 10): Promise<TopVendorsResponse> {
    return this.request<TopVendorsResponse>(
      `/analytics/top-vendors?limit=${limit}`
    );
  }

  async getExtractionSummary(): Promise<ExtractionSummary> {
    return this.request<ExtractionSummary>("/analytics/extraction-summary");
  }

  async getRagStatus(): Promise<RagStatus> {
    return this.request<RagStatus>("/rag/status");
  }

  async getRagIndexedDocuments(): Promise<RagIndexedDocuments> {
    return this.request<RagIndexedDocuments>("/rag/documents-indexed");
  }

  async indexDocuments(): Promise<RagIndexResponse> {
    return this.request<RagIndexResponse>("/rag/index-documents", {
      method: "POST",
    });
  }

  async askRagQuestion(
    question: string,
    topK = 5
  ): Promise<RagAnswer> {
    return this.request<RagAnswer>("/rag/ask", {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    });
  }

  async askDocumentQuestion(
    documentId: number,
    question: string,
    topK = 5
  ): Promise<RagAnswer> {
    return this.request<RagAnswer>(`/rag/ask-document/${documentId}`, {
      method: "POST",
      body: JSON.stringify({ question, top_k: topK }),
    });
  }
}

export class ApiRequestError extends Error {
  status: number;
  url?: string;

  constructor(message: string, status: number, url?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.url = url;
  }
}

export const api = new ApiClient();
