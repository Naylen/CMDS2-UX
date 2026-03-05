/** Logs — browse categories, runs, and log content with search. */
import { useEffect, useState } from "react";
import { Card, Col, Input, List, Row, Select, Typography, message } from "antd";
import {
  getLogCategories,
  getLogContent,
  getLogRuns,
  searchLogs,
} from "@/api/endpoints";
import LogStream from "@/components/LogStream";
import type { LogCategory, LogContent, LogRun } from "@/types";

const { Title, Text } = Typography;

export default function Logs() {
  const [mode, setMode] = useState("cloud");
  const [categories, setCategories] = useState<LogCategory[]>([]);
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [runs, setRuns] = useState<LogRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [content, setContent] = useState<LogContent | null>(null);
  const [searchResults, setSearchResults] = useState<
    { file: string; line_number: number; content: string }[] | null
  >(null);

  useEffect(() => {
    getLogCategories(mode)
      .then((r) => setCategories(r.data))
      .catch(() => {});
  }, [mode]);

  const onSelectCategory = (cat: string) => {
    setSelectedCat(cat);
    setSelectedRun(null);
    setContent(null);
    setSearchResults(null);
    getLogRuns(cat, mode)
      .then((r) => setRuns(r.data))
      .catch(() => {});
  };

  const onSelectRun = (runId: string) => {
    if (!selectedCat) return;
    setSelectedRun(runId);
    setSearchResults(null);
    getLogContent(selectedCat, runId, mode)
      .then((r) => setContent(r.data))
      .catch(() => message.error("Failed to load log content"));
  };

  const onSearch = (q: string) => {
    if (!q) return;
    searchLogs(q, mode)
      .then((r) => setSearchResults(r.data.results))
      .catch(() => message.error("Search failed"));
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Log Viewer</Title>
        <div style={{ display: "flex", gap: 8 }}>
          <Select value={mode} onChange={setMode} style={{ width: 120 }}>
            <Select.Option value="cloud">Cloud</Select.Option>
            <Select.Option value="hybrid">Hybrid</Select.Option>
          </Select>
          <Input.Search
            placeholder="Search logs by IP or keyword..."
            allowClear
            style={{ width: 300 }}
            onSearch={onSearch}
          />
        </div>
      </div>

      <Row gutter={16}>
        {/* Categories */}
        <Col xs={24} md={5}>
          <Card title="Categories" size="small">
            <List
              size="small"
              dataSource={categories}
              renderItem={(cat) => (
                <List.Item
                  onClick={() => onSelectCategory(cat.name)}
                  style={{
                    cursor: "pointer",
                    background: cat.name === selectedCat ? "#e6f4ff" : undefined,
                    padding: "8px 12px",
                  }}
                >
                  <span>{cat.name}</span>
                  <span style={{ color: "#999" }}>{cat.run_count}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Runs */}
        <Col xs={24} md={5}>
          <Card title="Runs" size="small">
            <List
              size="small"
              dataSource={runs}
              locale={{ emptyText: "Select a category" }}
              style={{ maxHeight: 600, overflow: "auto" }}
              renderItem={(run) => (
                <List.Item
                  onClick={() => onSelectRun(run.run_id)}
                  style={{
                    cursor: "pointer",
                    background: run.run_id === selectedRun ? "#e6f4ff" : undefined,
                    padding: "8px 12px",
                    fontSize: 12,
                  }}
                >
                  {run.run_id}
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* Content */}
        <Col xs={24} md={14}>
          {searchResults ? (
            <Card title={`Search Results (${searchResults.length})`} size="small">
              <List
                size="small"
                dataSource={searchResults}
                style={{ maxHeight: 600, overflow: "auto" }}
                renderItem={(r) => (
                  <List.Item>
                    <div>
                      <Text code style={{ fontSize: 11 }}>
                        {r.file}:{r.line_number}
                      </Text>
                      <div
                        style={{
                          fontFamily: "monospace",
                          fontSize: 12,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-all",
                          marginTop: 4,
                        }}
                      >
                        {r.content}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          ) : content ? (
            <LogStream
              lines={content.lines}
              title={`${selectedRun} (${content.total_lines} lines)`}
              maxHeight={600}
            />
          ) : (
            <Card>
              <Text type="secondary">Select a category and run to view logs.</Text>
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
