/** Shared TypeScript types mirroring backend Pydantic schemas. */

export interface ServiceStatus {
  name: string;
  state: "active" | "inactive" | "unknown";
}

export interface WorkflowStep {
  label: string;
  done: boolean;
}

export interface DashboardStatus {
  services: ServiceStatus[];
  cloud_steps: WorkflowStep[];
  hybrid_steps: WorkflowStep[];
  running_jobs: number;
  device_counts: Record<string, number>;
}

export interface SetupConfig {
  MERAKI_API_KEY: string;
  SSH_USERNAME: string;
  SSH_PASSWORD: string;
  ENABLE_PASSWORD: string;
  DISCOVERY_IPS: string;
  DISCOVERY_NETWORKS: string;
  DNS_PRIMARY: string;
  DNS_SECONDARY: string;
  HTTP_CLIENT_SOURCE_IFACE: string;
  FW_CAT9K_FILE: string;
  FW_CAT9K_LITE_FILE: string;
}

export interface TestResult {
  success: boolean;
  message: string;
}

export interface DiscoveryDevice {
  ip: string;
  hostname: string;
  pid: string;
  serial: string;
  ssh: boolean;
  login: boolean;
  blacklisted: boolean;
  backup_status: string;
  backup_path: string;
  uplink_type: string;
}

export interface DiscoveryResults {
  devices: DiscoveryDevice[];
  total: number;
  eligible: number;
}

export interface FirmwareImage {
  filename: string;
  size_bytes: number;
  size_human: string;
  modified: string;
}

export interface PreflightResult {
  ip: string;
  hostname: string;
  model: string;
  ios_ver: string;
  dns_ok: string;
  http_client_ok: string;
  ping_meraki: string;
  ready: string;
  notes: string;
}

export interface JobResponse {
  job_id: string;
  script: string;
  mode: string;
  category: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  message: string;
  exit_code: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface JobStartResponse {
  job_id: string;
  status: string;
}

export interface LogCategory {
  name: string;
  path: string;
  run_count: number;
}

export interface LogRun {
  run_id: string;
  timestamp: string;
  path: string;
}

export interface LogContent {
  run_id: string;
  lines: string[];
  total_lines: number;
}

export interface CleanPreview {
  files: string[];
  total: number;
}

export interface ModelEntry {
  model: string;
  family: string;
  image_type: string;
  min_version: string;
}

export interface BackupConfig {
  ip: string;
  hostname: string;
  filename: string;
  size_bytes: number;
  modified: string;
}

export interface ScheduledJob {
  job_number: string;
  scheduled_time: string;
  command: string;
}

// WebSocket message types
export interface WsProgress {
  type: "progress";
  job_id: string;
  pct: number;
  msg: string;
}

export interface WsLog {
  type: "log";
  job_id: string;
  line: string;
}

export interface WsComplete {
  type: "complete";
  job_id: string;
  exit_code: number;
  status: string;
}

export type WsMessage = WsProgress | WsLog | WsComplete | { type: string; [key: string]: unknown };
