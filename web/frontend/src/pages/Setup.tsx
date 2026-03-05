/** Setup Wizard — configure credentials, targets, and firmware selection. */
import { useEffect, useState } from "react";
import { Button, Card, Col, Divider, Form, Input, message, Row, Space, Tag, Typography } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { getSetup, saveSetup, testApi, testSsh } from "@/api/endpoints";
import type { SetupConfig, TestResult } from "@/types";

const { Title, Text } = Typography;

export default function Setup() {
  const [form] = Form.useForm<SetupConfig>();
  const [saving, setSaving] = useState(false);
  const [sshResult, setSshResult] = useState<TestResult | null>(null);
  const [apiResult, setApiResult] = useState<TestResult | null>(null);
  const [sshTesting, setSshTesting] = useState(false);
  const [apiTesting, setApiTesting] = useState(false);

  useEffect(() => {
    getSetup()
      .then((r) => form.setFieldsValue(r.data))
      .catch(() => {});
  }, [form]);

  const onSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const res = await saveSetup(values);
      form.setFieldsValue(res.data);
      message.success("Configuration saved");
    } catch {
      message.error("Save failed");
    } finally {
      setSaving(false);
    }
  };

  const onTestSsh = async () => {
    const values = await form.validateFields();
    setSshTesting(true);
    setSshResult(null);
    try {
      const res = await testSsh(values);
      setSshResult(res.data);
    } catch {
      setSshResult({ success: false, message: "Test request failed" });
    } finally {
      setSshTesting(false);
    }
  };

  const onTestApi = async () => {
    const values = await form.validateFields();
    setApiTesting(true);
    setApiResult(null);
    try {
      const res = await testApi(values);
      setApiResult(res.data);
    } catch {
      setApiResult({ success: false, message: "Test request failed" });
    } finally {
      setApiTesting(false);
    }
  };

  const ResultTag = ({ result }: { result: TestResult | null }) => {
    if (!result) return null;
    return (
      <Tag
        icon={result.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
        color={result.success ? "success" : "error"}
        style={{ marginLeft: 8 }}
      >
        {result.message}
      </Tag>
    );
  };

  return (
    <div>
      <Title level={4}>Setup Wizard</Title>
      <Text type="secondary">
        Configure Meraki API key, SSH credentials, target switches, and firmware selection.
      </Text>

      <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
        <Row gutter={24}>
          <Col xs={24} md={12}>
            <Card title="Meraki API">
              <Form.Item label="API Key" name="MERAKI_API_KEY">
                <Input.Password placeholder="Meraki Dashboard API Key" />
              </Form.Item>
              <Button onClick={onTestApi} loading={apiTesting}>
                Test API Connection
              </Button>
              <ResultTag result={apiResult} />
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="SSH Credentials">
              <Form.Item label="Username" name="SSH_USERNAME">
                <Input placeholder="admin" />
              </Form.Item>
              <Form.Item label="Password" name="SSH_PASSWORD">
                <Input.Password placeholder="SSH password" />
              </Form.Item>
              <Form.Item label="Enable Password" name="ENABLE_PASSWORD">
                <Input.Password placeholder="Enable password (optional)" />
              </Form.Item>
              <Button onClick={onTestSsh} loading={sshTesting}>
                Test SSH Connection
              </Button>
              <ResultTag result={sshResult} />
            </Card>
          </Col>
        </Row>

        <Row gutter={24} style={{ marginTop: 16 }}>
          <Col xs={24} md={12}>
            <Card title="Target Switches">
              <Form.Item label="Discovery IPs" name="DISCOVERY_IPS">
                <Input.TextArea rows={3} placeholder="Space-separated IPs" />
              </Form.Item>
              <Form.Item label="Discovery Networks (CIDR)" name="DISCOVERY_NETWORKS">
                <Input.TextArea rows={2} placeholder="e.g. 10.1.1.0/24 10.2.0.0/16" />
              </Form.Item>
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="Network Settings">
              <Form.Item label="Primary DNS" name="DNS_PRIMARY">
                <Input placeholder="e.g. 8.8.8.8" />
              </Form.Item>
              <Form.Item label="Secondary DNS" name="DNS_SECONDARY">
                <Input placeholder="e.g. 8.8.4.4" />
              </Form.Item>
              <Form.Item label="HTTP Client Source Interface" name="HTTP_CLIENT_SOURCE_IFACE">
                <Input placeholder="e.g. Vlan100" />
              </Form.Item>
            </Card>
          </Col>
        </Row>

        <Row gutter={24} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <Card title="Firmware Selection">
              <Row gutter={16}>
                <Col xs={12}>
                  <Form.Item label="Universal Firmware" name="FW_CAT9K_FILE">
                    <Input placeholder="e.g. cat9k_iosxe.17.15.01.SPA.bin" />
                  </Form.Item>
                </Col>
                <Col xs={12}>
                  <Form.Item label="LITE Firmware" name="FW_CAT9K_LITE_FILE">
                    <Input placeholder="e.g. cat9k_lite_iosxe.17.15.01.SPA.bin" />
                  </Form.Item>
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <Divider />
        <Space>
          <Button type="primary" size="large" onClick={onSave} loading={saving}>
            Save Configuration
          </Button>
        </Space>
      </Form>
    </div>
  );
}
