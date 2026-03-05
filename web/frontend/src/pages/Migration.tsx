/** Migration — claim devices into Meraki cloud and view inventory. */
import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Typography, message } from "antd";
import { SwapOutlined, ReloadOutlined } from "@ant-design/icons";
import { getMigrationInventory, startMigration } from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";

const { Title, Text } = Typography;

export default function Migration() {
  const [inventory, setInventory] = useState<Record<string, unknown>[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadInventory = () => {
    getMigrationInventory()
      .then((r) => setInventory(r.data.devices || []))
      .catch(() => {});
  };

  useEffect(() => { loadInventory(); }, []);

  const onStart = async () => {
    setLoading(true);
    try {
      const res = await startMigration();
      setJobId(res.data.job_id);
      message.info("Migration started");
    } catch {
      message.error("Failed to start migration");
    } finally {
      setLoading(false);
    }
  };

  // Dynamic columns from inventory data
  const cols = inventory.length > 0
    ? Object.keys(inventory[0]!).slice(0, 8).map((k) => ({
        title: k,
        dataIndex: k,
        key: k,
        ellipsis: true,
        render: (v: unknown) => String(v ?? ""),
      }))
    : [];

  return (
    <div>
      <Title level={4}>Meraki Migration</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
        Claim Catalyst switches into the Meraki cloud dashboard.
      </Text>

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<SwapOutlined />} onClick={onStart} loading={loading}>
          Start Migration
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadInventory}>
          Refresh Inventory
        </Button>
      </Space>

      <JobProgress
        jobId={jobId}
        title="Migration Progress"
        onComplete={() => { loadInventory(); message.success("Migration complete"); }}
      />

      <Card title={`Meraki Inventory (${inventory.length} devices)`} style={{ marginTop: 16 }}>
        <Table
          dataSource={inventory}
          columns={cols}
          rowKey={(r) => (r as Record<string, string>).serial || String(Math.random())}
          size="small"
          pagination={{ pageSize: 50 }}
          scroll={{ x: true }}
        />
      </Card>
    </div>
  );
}
