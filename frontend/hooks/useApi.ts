"use client";

import { useState, useEffect, useCallback } from "react";

export function useApi<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [fetcher]);

  useEffect(() => {
    const timeout = window.setTimeout(refetch, 0);
    return () => window.clearTimeout(timeout);
  }, [refetch]);

  return { data, loading, error, refetch };
}
