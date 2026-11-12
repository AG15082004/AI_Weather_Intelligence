import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

/**
 * TN Weather Intelligence API Client
 * Configured for local development and Render production environments.
 *
 * Precedence:
 * 1. import.meta.env.VITE_API_BASE_URL (explicit environment variable)
 * 2. Production mode default: https://ai-weather-intelligence.onrender.com
 * 3. Local development fallback: http://127.0.0.1:8000
 */
export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim() !== "") {
    return envUrl.trim().replace(/\/+$/, "").replace(/\/api$/, "");
  }
  if (import.meta.env.PROD) {
    return "https://ai-weather-intelligence.onrender.com";
  }
  return "http://127.0.0.1:8000";
}

// Ensure trailing slashes are removed from baseURL
export const API_BASE_URL = getApiBaseUrl();

// Extended config to track retry counts
interface RetryConfig extends AxiosRequestConfig {
  _retryCount?: number;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for Fabric SQL analytics queries & Render wake-up
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Request interceptor: normalize endpoint paths and strip empty query params
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // If url does not start with http:// or https://, normalize path and prevent duplicate /api
    if (
      config.url &&
      !config.url.startsWith("http://") &&
      !config.url.startsWith("https://")
    ) {
      let normalized = config.url.replace(/^\/+/, "/");
      if (normalized.startsWith("/api/api/")) {
        normalized = normalized.replace(/^\/api\/api\//, "/api/");
      } else if (!normalized.startsWith("/api/")) {
        normalized = `/api${normalized}`;
      }
      config.url = normalized;
    }

    // Clean up empty params
    if (config.params && typeof config.params === "object") {
      const cleanedParams: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(
        config.params as Record<string, unknown>
      )) {
        if (value !== undefined && value !== null && value !== "") {
          cleanedParams[key] = value;
        }
      }
      config.params = cleanedParams;
    }

    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor: handle retries for transient errors & produce clean errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: unknown; message?: string }>) => {
    const config = error.config as RetryConfig | undefined;

    // Retry transient failures (502, 503, 504, ECONNABORTED, ERR_NETWORK) on GET
    const isGet = (config?.method || "get").toLowerCase() === "get";
    const status = error.response?.status;
    const isTransient =
      status === 502 ||
      status === 503 ||
      status === 504 ||
      error.code === "ECONNABORTED" ||
      error.code === "ERR_NETWORK";

    if (config && isGet && isTransient) {
      config._retryCount = config._retryCount || 0;
      const MAX_RETRIES = 2;

      if (config._retryCount < MAX_RETRIES) {
        config._retryCount += 1;
        const delayMs = config._retryCount * 1500;
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        return apiClient(config as InternalAxiosRequestConfig);
      }
    }

    // Build user-friendly, secure error message
    let message = "An unexpected network error occurred.";

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 404) {
        message = "The requested weather data endpoint was not found.";
      } else if (status === 400 || status === 422) {
        if (typeof data?.detail === "string") {
          message = data.detail;
        } else if (Array.isArray(data?.detail)) {
          message = data.detail
            .map((item: { msg?: string }) => item.msg || "Invalid parameter")
            .join(", ");
        } else {
          message = "Invalid request parameters provided.";
        }
      } else if (status === 401 || status === 403) {
        message = "Access to the requested weather intelligence resource was denied.";
      } else if (status === 502 || status === 503 || status === 504) {
        message = `The cloud weather service is waking up or temporarily unavailable (HTTP ${status}). On Render free tier, spin-up from sleep takes ~50s. Please retry in a few moments.`;
      } else if (status >= 500) {
        message = `Weather analytics service encountered an internal error (HTTP ${status}). Please retry shortly.`;
      } else if (typeof data?.detail === "string") {
        message = data.detail;
      } else if (data?.message) {
        message = data.message;
      } else {
        message = `Server responded with status ${status}`;
      }
    } else if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      message =
        "Query timed out. Microsoft Fabric or the analytics engine took too long to respond. The service may be warming up; please retry.";
    } else if (error.request || error.code === "ERR_NETWORK") {
      message = `Unable to reach the TN Weather Intelligence API server at ${API_BASE_URL}. If the backend is waking up from sleep on Render, it takes ~50 seconds. Please wait a moment and click retry.`;
    } else if (error.message) {
      message = error.message;
    }

    const enhancedError = new Error(message);
    return Promise.reject(enhancedError);
  }
);

// In-flight GET request deduplication cache to prevent simultaneous duplicate roundtrips
const pendingGetRequests = new Map<string, Promise<any>>();

export async function deduplicatedGet<T = any>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const cacheKey = `${url}?${JSON.stringify(config?.params || {})}`;
  const existing = pendingGetRequests.get(cacheKey);
  if (existing) {
    return existing;
  }

  const promise = apiClient
    .get<T>(url, config)
    .then((res) => res.data)
    .finally(() => {
      pendingGetRequests.delete(cacheKey);
    });

  pendingGetRequests.set(cacheKey, promise);
  return promise;
}
