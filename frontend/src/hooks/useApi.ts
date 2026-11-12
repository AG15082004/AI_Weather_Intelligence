import { useCallback, useEffect, useRef, useState } from "react";

export interface UseApiOptions {
  enabled?: boolean;
}

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useApi<T, P = undefined>(
  apiFunction: (params?: P) => Promise<T>,
  params?: P,
  options?: UseApiOptions
): UseApiResult<T> {
  const enabled = options?.enabled ?? true;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [error, setError] = useState<string | null>(null);

  const requestCounterRef = useRef(0);
  const paramsKey = JSON.stringify(params ?? null);

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    const currentRequestId = ++requestCounterRef.current;
    setLoading(true);
    setError(null);

    try {
      const result = await apiFunction(params);
      if (requestCounterRef.current === currentRequestId) {
        setData(result);
      }
    } catch (err) {
      if (requestCounterRef.current === currentRequestId) {
        const message =
          err instanceof Error ? err.message : "Failed to load live data.";
        setError(message);
      }
    } finally {
      if (requestCounterRef.current === currentRequestId) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiFunction, paramsKey, enabled]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}
