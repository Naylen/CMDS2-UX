/** Typed API functions wrapping axios calls. */
import api from "./client";
import type {
  BackupConfig,
  CleanPreview,
  DashboardStatus,
  DiscoveryResults,
  FirmwareImage,
  JobResponse,
  JobStartResponse,
  LogCategory,
  LogContent,
  LogRun,
  ModelEntry,
  PreflightResult,
  ScheduledJob,
  ServiceStatus,
  SetupConfig,
  TestResult,
} from "@/types";

// ── Auth ──
export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password });
export const logout = () => api.post("/auth/logout");
export const getMe = () => api.get<{ username: string }>("/auth/me");

// ── Status ──
export const getStatus = () => api.get<DashboardStatus>("/status");
export const getServices = () => api.get<ServiceStatus[]>("/status/services");

// ── Cloud Setup ──
export const getSetup = () => api.get<SetupConfig>("/cloud/setup");
export const saveSetup = (config: SetupConfig) =>
  api.post<SetupConfig>("/cloud/setup", config);
export const testSsh = (config: SetupConfig) =>
  api.post<TestResult>("/cloud/setup/test-ssh", config);
export const testApi = (config: SetupConfig) =>
  api.post<TestResult>("/cloud/setup/test-api", config);

// ── Cloud Discovery ──
export const startDiscovery = () =>
  api.post<JobStartResponse>("/cloud/discovery/start");
export const getDiscoveryResults = () =>
  api.get<DiscoveryResults>("/cloud/discovery/results");
export const selectDevices = (ips: string[]) =>
  api.post("/cloud/discovery/select", { ips });

// ── Cloud Firmware ──
export const listImages = () => api.get<FirmwareImage[]>("/cloud/firmware/images");
export const deleteImage = (filename: string) =>
  api.delete(`/cloud/firmware/images/${filename}`);
export const startUpgrade = () =>
  api.post<JobStartResponse>("/cloud/firmware/upgrade");
export const listSchedules = () =>
  api.get<ScheduledJob[]>("/cloud/firmware/schedules");

// ── Cloud Preflight ──
export const startPreflight = () =>
  api.post<JobStartResponse>("/cloud/preflight/start");
export const fixDns = () =>
  api.post<JobStartResponse>("/cloud/preflight/fix-dns");
export const fixHttp = () =>
  api.post<JobStartResponse>("/cloud/preflight/fix-http");
export const getPreflightResults = () =>
  api.get<PreflightResult[]>("/cloud/preflight/results");
export const getPreflightReady = () =>
  api.get<{ ready: boolean }>("/cloud/preflight/ready");

// ── Cloud Migration ──
export const startMigration = () =>
  api.post<JobStartResponse>("/cloud/migration/start");
export const getMigrationInventory = () =>
  api.get("/cloud/migration/inventory");

// ── Cloud Ports ──
export const startAutoPortMigration = () =>
  api.post<JobStartResponse>("/cloud/ports/auto");
export const startMgmtIpMigration = () =>
  api.post<JobStartResponse>("/cloud/ports/mgmt-ip");

// ── Cloud Clean ──
export const previewClean = () => api.get<CleanPreview>("/cloud/clean/preview");
export const startClean = () =>
  api.post<JobStartResponse>("/cloud/clean/start");

// ── Logs ──
export const getLogCategories = (mode?: string) =>
  api.get<LogCategory[]>("/logs/categories", { params: { mode } });
export const getLogRuns = (category: string, mode?: string) =>
  api.get<LogRun[]>(`/logs/${category}/runs`, { params: { mode } });
export const getLogContent = (category: string, runId: string, mode?: string, file?: string) =>
  api.get<LogContent>(`/logs/${category}/${runId}`, { params: { mode, file } });
export const searchLogs = (q: string, mode?: string) =>
  api.get("/logs/search", { params: { q, mode } });

// ── Admin ──
export const getAdminServices = () =>
  api.get<ServiceStatus[]>("/admin/services");
export const controlService = (name: string, action: string) =>
  api.post(`/admin/services/${name}`, null, { params: { action } });
export const runBackup = () => api.post("/admin/backup");
export const getSystemInfo = () => api.get("/admin/system-info");

// ── Util ──
export const getMatrix = () => api.get<ModelEntry[]>("/util/matrix");
export const getConfigs = () => api.get<BackupConfig[]>("/util/configs");
export const getConfigContent = (filename: string) =>
  api.get<{ filename: string; content: string }>(`/util/configs/${filename}`);
export const getJobs = (mode?: string, category?: string) =>
  api.get<JobResponse[]>("/util/jobs", { params: { mode, category } });
export const getJob = (jobId: string) =>
  api.get<JobResponse>(`/util/jobs/${jobId}`);
export const getJobLogs = (jobId: string) =>
  api.get<{ job_id: string; lines: string[]; total: number }>(`/util/jobs/${jobId}/logs`);
export const cancelJob = (jobId: string) =>
  api.post(`/util/jobs/${jobId}/cancel`);
