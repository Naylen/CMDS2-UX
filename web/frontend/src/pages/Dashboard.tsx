/** Dashboard — system health, workflow progress, device stats. */
import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Tag, Typography } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { getStatus } from "@/api/endpoints";
import WorkflowStepper from "@/components/WorkflowStepper";
import type { DashboardStatus } from "@/types";

const { Title } = Typography;

export default function Dashboard() {
  const [data, setData] = useState<DashboardStatus | null>(null);

  const load = () => {
    getStatus()
      .then((r) => setData(r.data))
      .catch(() => {});
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 10000);
    return () => clearInterval(iv);
  }, []);

  if (!data) return null;

  return (
    <div>
      <Title level={4} style={{ marginBottom: 20 }}>Dashboard</Title>

      {/* Service Health */}
      <Row gutter={[16, 16]}>
        {data.services.map((s) => (
          <Col key={s.name} xs={12} sm={8} md={6}>
            <Card size="small">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 500, textTransform: "uppercase", fontSize: 12 }}>
                  {s.name}
                </span>
                <Tag
                  icon={
                    s.state === "active" ? (
                      <CheckCircleOutlined />
                    ) : (
                      <CloseCircleOutlined />
                    )
                  }
                  color={s.state === "active" ? "success" : "error"}
                >
                  {s.state}
                </Tag>
              </div>
            </Card>
          </Col>
        ))}
        <Col xs={12} sm={8} md={6}>
          <Card size="small">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 500, fontSize: 12 }}>RUNNING JOBS</span>
              {data.running_jobs > 0 ? (
                <Tag icon={<SyncOutlined spin />} color="processing">
                  {data.running_jobs}
                </Tag>
              ) : (
                <Tag>0</Tag>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Device Counts */}
      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        {Object.entries(data.device_counts).map(([key, val]) => (
          <Col key={key} xs={12} sm={6}>
            <Card>
              <Statistic
                title={key.charAt(0).toUpperCase() + key.slice(1)}
                value={val}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Workflow Progress */}
      <Row gutter={[16, 16]} style={{ marginTop: 20 }}>
        <Col xs={24} md={12}>
          <Card title="Cloud Workflow">
            <WorkflowStepper steps={data.cloud_steps} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Hybrid Workflow">
            <WorkflowStepper steps={data.hybrid_steps} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
