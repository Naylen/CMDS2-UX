/** Clean — preview and reset state for a new batch. */
import { useEffect, useState } from "react";
import { Button, Card, List, Popconfirm, Typography, message } from "antd";
import { DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import { previewClean, startClean } from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";
import type { CleanPreview } from "@/types";

const { Title, Text } = Typography;

export default function Clean() {
  const [preview, setPreview] = useState<CleanPreview | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    previewClean().then((r) => setPreview(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const onClean = async () => {
    setLoading(true);
    try {
      const res = await startClean();
      setJobId(res.data.job_id);
      message.info("Clean started");
    } catch {
      message.error("Failed to start clean");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={4}>Clean — New Batch</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 20 }}>
        Remove previous run artifacts to prepare for a new deployment batch.
        This will NOT remove cloud_models.json or runs/ history.
      </Text>

      <Card
        title={`Files to Remove (${preview?.total ?? 0})`}
        extra={<Button icon={<EyeOutlined />} onClick={load}>Refresh Preview</Button>}
      >
        <List
          size="small"
          dataSource={preview?.files ?? []}
          renderItem={(f) => <List.Item>{f}</List.Item>}
          locale={{ emptyText: "No files to clean" }}
          style={{ maxHeight: 400, overflow: "auto" }}
        />
      </Card>

      <div style={{ marginTop: 16 }}>
        <Popconfirm
          title="This will delete all listed files. Continue?"
          onConfirm={onClean}
          okText="Yes, Clean"
          okButtonProps={{ danger: true }}
        >
          <Button
            type="primary"
            danger
            icon={<DeleteOutlined />}
            size="large"
            loading={loading}
            disabled={!preview?.total}
          >
            Clean All Artifacts
          </Button>
        </Popconfirm>
      </div>

      <JobProgress
        jobId={jobId}
        title="Clean Progress"
        onComplete={() => { load(); message.success("Clean complete"); }}
      />
    </div>
  );
}
