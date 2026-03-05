import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Layout, Menu, Button, Typography, theme } from "antd";
import {
  DashboardOutlined,
  SettingOutlined,
  SearchOutlined,
  CloudUploadOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  ApiOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ToolOutlined,
  LogoutOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
import { useAuth } from "@/auth/AuthContext";

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
  {
    key: "cloud",
    icon: <AppstoreOutlined />,
    label: "Cloud Workflow",
    children: [
      { key: "/cloud/setup", icon: <SettingOutlined />, label: "Setup Wizard" },
      { key: "/cloud/discovery", icon: <SearchOutlined />, label: "Discovery" },
      { key: "/cloud/firmware", icon: <CloudUploadOutlined />, label: "Firmware" },
      { key: "/cloud/preflight", icon: <SafetyCertificateOutlined />, label: "Preflight" },
      { key: "/cloud/migration", icon: <SwapOutlined />, label: "Migration" },
      { key: "/cloud/ports", icon: <ApiOutlined />, label: "Port Config" },
      { key: "/cloud/clean", icon: <DeleteOutlined />, label: "Clean" },
    ],
  },
  { key: "/logs", icon: <FileTextOutlined />, label: "Logs" },
  { key: "/admin", icon: <ToolOutlined />, label: "Admin" },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { token } = theme.useToken();

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}
      >
        <div
          style={{
            height: 48,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Text strong style={{ fontSize: collapsed ? 14 : 18, color: token.colorPrimary }}>
            {collapsed ? "C2" : "CMDS2"}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={["cloud"]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: token.colorBgContainer,
            padding: "0 24px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Text style={{ marginRight: 16 }}>{user}</Text>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={logout}
          >
            Logout
          </Button>
        </Header>
        <Content style={{ margin: 24, overflow: "auto" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
