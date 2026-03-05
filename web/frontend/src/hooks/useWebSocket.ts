/** Hook for subscribing to WebSocket job updates. */
import { useEffect, useRef, useState } from "react";
import { wsClient } from "@/api/websocket";
import type { WsMessage } from "@/types";

export function useJobProgress(jobId: string | null) {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [completed, setCompleted] = useState(false);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const logsRef = useRef<string[]>([]);

  useEffect(() => {
    if (!jobId) return;

    // Reset state for new job
    setProgress(0);
    setMessage("");
    setLogs([]);
    setCompleted(false);
    setExitCode(null);
    logsRef.current = [];

    wsClient.connect();
    wsClient.subscribe(jobId);

    const unsub = wsClient.onMessage((msg: WsMessage) => {
      if ("job_id" in msg && msg.job_id !== jobId) return;

      switch (msg.type) {
        case "progress":
          if ("pct" in msg) setProgress(msg.pct as number);
          if ("msg" in msg) setMessage(msg.msg as string);
          break;
        case "log":
          if ("line" in msg) {
            const line = msg.line as string;
            logsRef.current = [...logsRef.current.slice(-499), line];
            setLogs([...logsRef.current]);
          }
          break;
        case "complete":
          setCompleted(true);
          if ("exit_code" in msg) setExitCode(msg.exit_code as number);
          if ("pct" in msg) setProgress(msg.pct as number);
          break;
      }
    });

    return () => {
      unsub();
      wsClient.unsubscribe(jobId);
    };
  }, [jobId]);

  return { progress, message, logs, completed, exitCode };
}
