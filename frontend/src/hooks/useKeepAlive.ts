/**
 * React hook to keep the backend warm during user sessions.
 * Pings the /health endpoint every 5 minutes while the user is active.
 * This prevents Render free-tier spin-down (15-minute idle timeout).
 */

import { useEffect, useRef } from 'react';
import { keepAlive } from '../services/api';

const PING_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function useKeepAlive(enabled: boolean = true) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!enabled) return;

    // Initial ping on mount
    keepAlive().catch(() => {});

    // Periodic ping every 5 minutes
    intervalRef.current = setInterval(() => {
      keepAlive().catch(() => {});
    }, PING_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [enabled]);
}
