import { useCallback, useReducer, useRef } from "react";
import { api } from "../api/client";
import type { Preferences } from "../api/types";
import { initialRunState, runReducer } from "./runReducer";

export function useBlogRun(userId: string) {
  const [state, dispatch] = useReducer(runReducer, initialRunState);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(
    async (message: string, preferences: Preferences) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: "start" });
      try {
        const { session_id } = await api.createSession(userId, preferences);
        await api.run(userId, session_id, message, (msg) => dispatch({ type: "message", msg }), controller.signal);
      } catch (err) {
        if ((err as Error).name !== "AbortError") dispatch({ type: "fail", error: (err as Error).message });
      }
    },
    [userId],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "reset" });
  }, []);

  return { state, start, cancel, reset: () => dispatch({ type: "reset" }) };
}
