/** Preflight — validation results with auto-fix options. */
import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import {
  fixDns,
  fixHttp,
  getPreflightReady,
  getPreflightResults,
  startPreflight,
} from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";
import type { PreflightResult } from "@/types";

const { Title } = Typography;

export default function Preflight() {
  const [results, setResults] = useState<PreflightResult[]>([]);
  const [ready, setReady] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    getPreflightResults().then((r) => setResults(r.data)).catch(() => {});
    getPreflightReady().then((r) => setReady(r.data.ready)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const onStart = async () => {
    setLoading(true);
    try {
      const res = await startPreflight();
      setJobId(res.data.job_id);
    } catch {
      message.error("Failed to start preflight");
    } finally {
      setLoading(false);
    }
  };

  const onFixDns = async () => {
    try {
      const res = await fixDns();
      setJobId(res.data.job_id);
      message.info("DNS fix started");
    } catch {
      message.error("Failed to start DNS fix");
    }
  };

  const onFixHttp = async () => {
    try {
      const res = await fixHttp();
      setJobId(res.data.job_id);
      message.info("HTTP fix started");
    } catch {
      message.error("Failed to start HTTP fix");
    }
  };

  const okTag = (v: string) => {
    const isOk = v.toLowerCase() === "ok" || v.toLowerCase() === "yes" || v === "1";
    return (
      <Tag
        icon={isOk ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        color={isOk ? "success" : "error"}
      >
        {v || "N/A"}
      </Tag>
    );
  };

  const columns = [
    { title: "IP", dataIndex: "ip", key: "ip" },
    { title: "Hostname", dataIndex: "hostname", key: "hostname" },
    { title: "Model", dataIndex: "model", key: "model" },
    { title: "IOS-XE", dataIndex: "ios_ver", key: "ios_ver" },
    { title: "DNS", dataIndex: "dns_ok", key: "dns_ok", render: okTag },
    { title: "HTTP Client", dataIndex: "http_client_ok", key: "http_client_ok", render: okTag },
    { title: "Ping Meraki", dataIndex: "ping_meraki", key: "ping_meraki", render: okTag },
    { title: "Ready", dataIndex: "ready", key: "ready", render: okTag },
    { title: "Notes", dataIndex: "notes", key: "notes", ellipsis: true },
  ];

  return (
    <div>
      <Title level={4}>
        Preflight Validation
        {ready && (
          <Tag color="success" style={{ marginLeft: 12, verticalAlign: "middle" }}>
            All Clear
          </Tag>
        )}
      </Title>

      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<SafetyCertificateOutlined />}
          onClick={onStart}
          loading={loading}
        >
          Run Preflight
        </Button>
        <Button icon={<ToolOutlined />} onClick={onFixDns}>
          Fix DNS
        </Button>
        <Button icon={<ToolOutlined />} onClick={onFixHttp}>
          Fix HTTP Client
        </Button>
      </Space>

      <JobProgress
        jobId={jobId}
        title="Preflight Progress"
        onComplete={() => { load(); message.success("Preflight complete"); }}
      />

      <Card style={{ marginTop: 16 }}>
        <Table
          dataSource={results}
          columns={columns}
          rowKey="ip"
          size="small"
          pagination={{ pageSize: 50 }}
        />
      </Card>
    </div>
  );
}
