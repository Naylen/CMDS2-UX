/** Admin — service control, backup, system info, jobs. */
import { useEffect, useState } from "react";
import { Button, Card, Col, Descriptions, Row, Space, Table, Tag, Typography, message } from "antd";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SaveOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import {
  cancelJob,
  controlService,
  getAdminServices,
  getJobs,
  getSystemInfo,
  runBackup,
} from "@/api/endpoints";
import type { JobResponse, ServiceStatus } from "@/types";

const { Title } = Typography;

export default function Admin() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [sysInfo, setSysInfo] = useState<Record<string, string>>({});
  const [backupLoading, setBackupLoading] = useState(false);

  const loadServices = () => {
    getAdminServices().then((r) => setServices(r.data)).catch(() => {});
  };
  const loadJobs = () => {
    getJobs().then((r) => setJobs(r.data)).catch(() => {});
  };
  const loadInfo = () => {
    getSystemInfo().then((r) => setSysInfo(r.data)).catch(() => {});
  };

  useEffect(() => {
    loadServices();
    loadJobs();
    loadInfo();
    const iv = setInterval(() => { loadServices(); loadJobs(); }, 10000);
    return () => clearInterval(iv);
  }, []);

  const onService = async (name: string, action: string) => {
    try {
      await controlService(name, action);
      message.success(`${name} ${action} OK`);
      loadServices();
    } catch {
      message.error(`Failed to ${action} ${name}`);
    }
  };

  const onBackup = async () => {
    setBackupLoading(true);
    try {
      await runBackup();
      message.success("Backup complete");
    } catch {
      message.error("Backup failed");
    } finally {
      setBackupLoading(false);
    }
  };

  const onCancel = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      message.success("Job cancelled");
      loadJobs();
    } catch {
      message.error("Failed to cancel job");
    }
  };

  const svcCols = [
    { title: "Service", dataIndex: "name", key: "name" },
    {
      title: "State",
      dataIndex: "state",
      key: "state",
      render: (v: string) => (
        <Tag color={v === "active" ? "success" : "error"}>{v}</Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, rec: ServiceStatus) => (
        <Space size="small">
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => onService(rec.name, "start")}
          >
            Start
          </Button>
          <Button
            size="small"
            icon={<PauseCircleOutlined />}
            onClick={() => onService(rec.name, "stop")}
          >
            Stop
          </Button>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => onService(rec.name, "restart")}
          >
            Restart
          </Button>
        </Space>
      ),
    },
  ];

  const jobCols = [
    { title: "Job ID", dataIndex: "job_id", key: "job_id", ellipsis: true },
    { title: "Category", dataIndex: "category", key: "category" },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => {
        const colors: Record<string, string> = {
          running: "processing",
          completed: "success",
          failed: "error",
          cancelled: "warning",
          pending: "default",
        };
        return <Tag color={colors[v] ?? "default"}>{v}</Tag>;
      },
    },
    { title: "Progress", dataIndex: "progress", key: "progress", render: (v: number) => `${v}%` },
    {
      title: "Started",
      dataIndex: "started_at",
      key: "started_at",
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, rec: JobResponse) =>
        rec.status === "running" ? (
          <Button size="small" danger onClick={() => onCancel(rec.job_id)}>
            Cancel
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <Title level={4}>Administration</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="Services">
            <Table
              dataSource={services}
              columns={svcCols}
              rowKey="name"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title="System Info"
            extra={<Button icon={<InfoCircleOutlined />} size="small" onClick={loadInfo}>Refresh</Button>}
          >
            <Descriptions column={1} size="small">
              {Object.entries(sysInfo).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {v}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
          <Card title="Backup" style={{ marginTop: 16 }}>
            <Button
              icon={<SaveOutlined />}
              onClick={onBackup}
              loading={backupLoading}
            >
              Run Backup Now
            </Button>
          </Card>
        </Col>
      </Row>

      <Card title="Job History" style={{ marginTop: 16 }}>
        <Table
          dataSource={jobs}
          columns={jobCols}
          rowKey="job_id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}
