/** Firmware — image management, upload, upgrade, and scheduling. */
import { useEffect, useState } from "react";
import {
  Button,
  message,
  Popconfirm,
  Space,
  Table,
  Tabs,
  Typography,
  Upload,
} from "antd";
import {
  DeleteOutlined,
  RocketOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  deleteImage,
  listImages,
  listSchedules,
  startUpgrade,
} from "@/api/endpoints";
import JobProgress from "@/components/JobProgress";
import type { FirmwareImage, ScheduledJob } from "@/types";

const { Title } = Typography;

export default function Firmware() {
  const [images, setImages] = useState<FirmwareImage[]>([]);
  const [schedules, setSchedules] = useState<ScheduledJob[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadImages = () => {
    listImages().then((r) => setImages(r.data)).catch(() => {});
  };
  const loadSchedules = () => {
    listSchedules().then((r) => setSchedules(r.data)).catch(() => {});
  };

  useEffect(() => {
    loadImages();
    loadSchedules();
  }, []);

  const onUpgrade = async () => {
    setLoading(true);
    try {
      const res = await startUpgrade();
      setJobId(res.data.job_id);
      message.info("Firmware upgrade started");
    } catch {
      message.error("Failed to start upgrade");
    } finally {
      setLoading(false);
    }
  };

  const onDelete = async (filename: string) => {
    try {
      await deleteImage(filename);
      message.success("Image deleted");
      loadImages();
    } catch {
      message.error("Failed to delete image");
    }
  };

  const imageCols = [
    { title: "Filename", dataIndex: "filename", key: "filename" },
    { title: "Size", dataIndex: "size_human", key: "size_human" },
    {
      title: "Modified",
      dataIndex: "modified",
      key: "modified",
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: unknown, rec: FirmwareImage) => (
        <Popconfirm title="Delete this image?" onConfirm={() => onDelete(rec.filename)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>Firmware Management</Title>

      <Tabs
        items={[
          {
            key: "images",
            label: "Image Library",
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Upload
                    action="/api/v1/cloud/firmware/upload"
                    withCredentials
                    showUploadList={false}
                    onChange={(info) => {
                      if (info.file.status === "done") {
                        message.success(`${info.file.name} uploaded`);
                        loadImages();
                      } else if (info.file.status === "error") {
                        message.error("Upload failed");
                      }
                    }}
                  >
                    <Button icon={<UploadOutlined />}>Upload Firmware</Button>
                  </Upload>
                </Space>
                <Table
                  dataSource={images}
                  columns={imageCols}
                  rowKey="filename"
                  size="small"
                  pagination={false}
                />
              </>
            ),
          },
          {
            key: "upgrade",
            label: "Run Upgrade",
            children: (
              <>
                <Button
                  type="primary"
                  icon={<RocketOutlined />}
                  onClick={onUpgrade}
                  loading={loading}
                  style={{ marginBottom: 16 }}
                >
                  Start Firmware Upgrade
                </Button>
                <JobProgress
                  jobId={jobId}
                  title="Firmware Upgrade Progress"
                  onComplete={() => message.success("Firmware upgrade finished")}
                />
              </>
            ),
          },
          {
            key: "scheduled",
            label: "Scheduled",
            children: (
              <Table
                dataSource={schedules}
                columns={[
                  { title: "Job #", dataIndex: "job_number", key: "job_number" },
                  { title: "Scheduled", dataIndex: "scheduled_time", key: "scheduled_time" },
                  { title: "Command", dataIndex: "command", key: "command" },
                ]}
                rowKey="job_number"
                size="small"
                pagination={false}
              />
            ),
          },
        ]}
      />
    </div>
  );
}
