import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ConfigProvider, Spin, theme } from "antd";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import LoginPage from "@/auth/LoginPage";
import MainLayout from "@/layouts/MainLayout";
import Dashboard from "@/pages/Dashboard";
import Setup from "@/pages/Setup";
import Discovery from "@/pages/Discovery";
import Firmware from "@/pages/Firmware";
import Preflight from "@/pages/Preflight";
import Migration from "@/pages/Migration";
import Ports from "@/pages/Ports";
import Clean from "@/pages/Clean";
import Logs from "@/pages/Logs";
import Admin from "@/pages/Admin";

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cloud/setup" element={<Setup />} />
        <Route path="/cloud/discovery" element={<Discovery />} />
        <Route path="/cloud/firmware" element={<Firmware />} />
        <Route path="/cloud/preflight" element={<Preflight />} />
        <Route path="/cloud/migration" element={<Migration />} />
        <Route path="/cloud/ports" element={<Ports />} />
        <Route path="/cloud/clean" element={<Clean />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  );
}
