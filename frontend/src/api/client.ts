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
const DEFAULT_PROD_API_URL = "https://ai-weather-intelligence.onrender.com";
const DEFAULT_DEV_API_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === "string" && envUrl.trim() !== "") {
    return envUrl.trim().replace(/\/+$/, "");
  }
  if (import.meta.env.PROD) {
    return DEFAULT_PROD_API_URL;
  }
  return DEFAULT_DEV_API_URL;
}

// Ensure trailing slashes are removed from baseURL
export const API_BASE_URL = getApiBaseUrl();

// Extended config to track retry counts
interface RetryConfig extends AxiosRequestConfig {
  _retryCount?: number;
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 25000, // 25 seconds for Fabric SQL analytics queries
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Request interceptor: normalize endpoint paths and strip empty query params
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // If url does not start with /api and is not an absolute URL, prepend /api
    if (
      config.url &&
      !config.url.startsWith("http://") &&
      !config.url.startsWith("https://")
    ) {
      if (!config.url.startsWith("/api")) {
        config.url = `/api${config.url.startsWith("/") ? "" : "/"}${config.url}`;
      }
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
        const delayMs = config._retryCount * 1000;
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        return apiClient(config as InternalAxiosRequestConfig);
      }
    }

    // Build user-friendly, secure error message
    let message = "An unexpected network error occurred.";

    if (error.response) {
      const data = error.response.data;
      if (typeof data?.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data?.detail)) {
        message = data.detail
          .map((item: { msg?: string }) => item.msg || "Validation error")
          .join(", ");
      } else if (data?.message) {
        message = data.message;
      } else {
        message = `Server responded with status ${error.response.status}`;
      }
    } else if (error.code === "ECONNABORTED") {
      message =
        "Lakehouse query timed out. The backend is processing or Microsoft Fabric is warming up.";
    } else if (error.request) {
      message = `Unable to reach the TN Weather Intelligence API server at ${API_BASE_URL}. Please verify the backend service is running.`;
    } else if (error.message) {
      message = error.message;
    }

    const enhancedError = new Error(message);
    return Promise.reject(enhancedError);
  }
);
