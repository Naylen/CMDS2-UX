/** Discovery — launch switch discovery, view results, select devices. */
import { useCallback, useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { ReloadOutlined, RocketOutlined } from "@ant-design/icons";
import {
  getDiscoveryResults,
  selectDevices,
  startDiscovery,
} from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";
import type { DiscoveryDevice } from "@/types";

const { Title, Text } = Typography;

export default function Discovery() {
  const [devices, setDevices] = useState<DiscoveryDevice[]>([]);
  const [total, setTotal] = useState(0);
  const [eligible, setEligible] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadResults = useCallback(() => {
    getDiscoveryResults()
      .then((r) => {
        setDevices(r.data.devices);
        setTotal(r.data.total);
        setEligible(r.data.eligible);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  const onStart = async () => {
    setLoading(true);
    try {
      const res = await startDiscovery();
      setJobId(res.data.job_id);
      message.info(`Discovery started: ${res.data.job_id}`);
    } catch {
      message.error("Failed to start discovery");
    } finally {
      setLoading(false);
    }
  };

  const onComplete = () => {
    loadResults();
    message.success("Discovery complete");
  };

  const onSelect = async () => {
    if (selected.length === 0) {
      message.warning("No devices selected");
      return;
    }
    try {
      await selectDevices(selected);
      message.success(`${selected.length} devices selected for operations`);
    } catch {
      message.error("Failed to save selection");
    }
  };

  const columns = [
    { title: "IP", dataIndex: "ip", key: "ip", sorter: (a: DiscoveryDevice, b: DiscoveryDevice) => a.ip.localeCompare(b.ip) },
    { title: "Hostname", dataIndex: "hostname", key: "hostname" },
    { title: "Model", dataIndex: "pid", key: "pid" },
    { title: "Serial", dataIndex: "serial", key: "serial" },
    {
      title: "SSH",
      dataIndex: "ssh",
      key: "ssh",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "OK" : "Fail"}</Tag>,
    },
    {
      title: "Login",
      dataIndex: "login",
      key: "login",
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "OK" : "Fail"}</Tag>,
    },
    { title: "Uplink", dataIndex: "uplink_type", key: "uplink_type" },
    { title: "Backup", dataIndex: "backup_status", key: "backup_status" },
  ];

  return (
    <div>
      <Title level={4}>Switch Discovery</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<RocketOutlined />}
          onClick={onStart}
          loading={loading}
        >
          Start Discovery
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadResults}>
          Refresh Results
        </Button>
        <Button type="default" onClick={onSelect} disabled={selected.length === 0}>
          Save Selection ({selected.length})
        </Button>
      </Space>

      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        {total} devices discovered, {eligible} eligible for operations
      </Text>

      <JobProgress jobId={jobId} title="Discovery Progress" onComplete={onComplete} />

      <Card style={{ marginTop: 16 }}>
        <Table
          dataSource={devices}
          columns={columns}
          rowKey="ip"
          size="small"
          pagination={{ pageSize: 50, showSizeChanger: true }}
          rowSelection={{
            selectedRowKeys: selected,
            onChange: (keys) => setSelected(keys as string[]),
            getCheckboxProps: (rec) => ({
              disabled: !rec.ssh || !rec.login || rec.blacklisted,
            }),
          }}
        />
      </Card>
    </div>
  );
}
