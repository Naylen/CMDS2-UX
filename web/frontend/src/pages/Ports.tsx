/** Port Config Migration — auto port and management IP migration. */
import { useState } from "react";
import { Button, Card, Col, Row, Typography, message } from "antd";
import { ApiOutlined, GlobalOutlined } from "@ant-design/icons";
import { startAutoPortMigration, startMgmtIpMigration } from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";

const { Title, Text } = Typography;

export default function Ports() {
  const [portJobId, setPortJobId] = useState<string | null>(null);
  const [ipJobId, setIpJobId] = useState<string | null>(null);
  const [portLoading, setPortLoading] = useState(false);
  const [ipLoading, setIpLoading] = useState(false);

  const onPortMigration = async () => {
    setPortLoading(true);
    try {
      const res = await startAutoPortMigration();
      setPortJobId(res.data.job_id);
      message.info("Port config migration started");
    } catch {
      message.error("Failed to start port migration");
    } finally {
      setPortLoading(false);
    }
  };

  const onIpMigration = async () => {
    setIpLoading(true);
    try {
      const res = await startMgmtIpMigration();
      setIpJobId(res.data.job_id);
      message.info("Management IP migration started");
    } catch {
      message.error("Failed to start IP migration");
    } finally {
      setIpLoading(false);
    }
  };

  return (
    <div>
      <Title level={4}>Port Configuration Migration</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 20 }}>
        Migrate IOS-XE port configurations and management IPs to Meraki cloud.
      </Text>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Auto Port Migration" extra={<ApiOutlined />}>
            <Text style={{ display: "block", marginBottom: 16 }}>
              Automatically translate IOS-XE interface configurations to Meraki
              switchport settings using backed-up running configs.
            </Text>
            <Button
              type="primary"
              icon={<ApiOutlined />}
              onClick={onPortMigration}
              loading={portLoading}
            >
              Start Port Migration
            </Button>
            <JobProgress
              jobId={portJobId}
              title="Port Migration"
              onComplete={() => message.success("Port migration complete")}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="Management IP Migration" extra={<GlobalOutlined />}>
            <Text style={{ display: "block", marginBottom: 16 }}>
              Configure management VLAN IP addresses on Meraki devices from
              the original IOS-XE SVI configuration.
            </Text>
            <Button
              type="primary"
              icon={<GlobalOutlined />}
              onClick={onIpMigration}
              loading={ipLoading}
            >
              Start IP Migration
            </Button>
            <JobProgress
              jobId={ipJobId}
              title="IP Migration"
              onComplete={() => message.success("IP migration complete")}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
