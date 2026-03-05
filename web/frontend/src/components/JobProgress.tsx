/** Real-time job progress bar with WebSocket streaming. */
import { useEffect, useRef } from "react";
import { Card, Progress, Typography, Tag } from "antd";
import { useJobProgress } from "@/hooks/useWebSocket";

const { Text } = Typography;

interface Props {
  jobId: string | null;
  title?: string;
  onComplete?: (exitCode: number | null) => void;
}

export default function JobProgress({ jobId, title, onComplete }: Props) {
  const { progress, message, logs, completed, exitCode } = useJobProgress(jobId);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (completed && onComplete) {
      onComplete(exitCode);
    }
  }, [completed, exitCode, onComplete]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (!jobId) return null;

  return (
    <Card
      title={title ?? `Job: ${jobId}`}
      extra={
        completed ? (
          <Tag color={exitCode === 0 ? "success" : "error"}>
            {exitCode === 0 ? "Completed" : `Failed (${exitCode})`}
          </Tag>
        ) : (
          <Tag color="processing">Running</Tag>
        )
      }
      style={{ marginTop: 16 }}
    >
      <Progress
        percent={progress}
        status={completed ? (exitCode === 0 ? "success" : "exception") : "active"}
        style={{ marginBottom: 8 }}
      />
      {message && (
        <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
          {message}
        </Text>
      )}
      <div
        style={{
          background: "#1a1a2e",
          color: "#e0e0e0",
          fontFamily: "monospace",
          fontSize: 12,
          padding: 12,
          borderRadius: 6,
          maxHeight: 300,
          overflow: "auto",
        }}
      >
        {logs.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
        <div ref={logEndRef} />
      </div>
    </Card>
  );
}
