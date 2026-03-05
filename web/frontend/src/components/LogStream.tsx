/** Real-time log viewer with auto-scroll and search. */
import { useEffect, useRef, useState } from "react";
import { Card, Input } from "antd";

interface Props {
  lines: string[];
  title?: string;
  maxHeight?: number;
}

export default function LogStream({ lines, title, maxHeight = 500 }: Props) {
  const [filter, setFilter] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const filtered = filter
    ? lines.filter((l) => l.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filtered]);

  return (
    <Card
      title={title ?? "Logs"}
      extra={
        <Input.Search
          placeholder="Filter..."
          allowClear
          size="small"
          style={{ width: 200 }}
          onSearch={setFilter}
          onChange={(e) => !e.target.value && setFilter("")}
        />
      }
    >
      <div
        style={{
          background: "#1a1a2e",
          color: "#e0e0e0",
          fontFamily: "monospace",
          fontSize: 12,
          padding: 12,
          borderRadius: 6,
          maxHeight,
          overflow: "auto",
          whiteSpace: "pre-wrap",
          wordBreak: "break-all",
        }}
      >
        {filtered.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
        <div ref={endRef} />
      </div>
    </Card>
  );
}
