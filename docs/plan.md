# CMDS2 Modernization Plan

## Project Overview

CMDS2 (Catalyst-to-Meraki Deployment Server) is a ~61 bash script platform on Rocky Linux that automates Cisco Catalyst-to-Meraki switch migrations. The modernization adds Docker containerization (Phase 1) and a web frontend (Phase 2) while preserving 100% of the existing TUI functionality.

**Repositories:**
- Upstream: `git@github.com:fumatchu/CMDS2.git` (remote: `origin`)
- UX Fork: `git@github.com:Naylen/CMDS2-UX.git` (remote: `ux`)

---

## Architecture

### Three Operating Modes
| Mode | Directory | Description |
|------|-----------|-------------|
| Cloud | `.cloud_admin/` | Full Meraki cloud migration (primary workflow) |
| Hybrid | `.hybrid_admin/` | Mixed on-prem + cloud |
| Catalyst Local | `.cat_admin/` | On-prem only upgrades |

### Core Workflow (7 Steps)
1. **Setup Wizard** — Configure Meraki API key, SSH credentials, target IPs, DNS, firmware
2. **Discovery** — Scan and probe switches via SSH (parallel pool)
3. **Firmware Upgrade** — Push IOS-XE images via TFTP/HTTP
4. **Preflight** — Validate DNS, HTTP client, Meraki reachability per switch
5. **Migration** — Claim devices into Meraki dashboard, create networks
6. **Port Config** — Auto per-port migration + management IP migration
7. **Clean** — Remove state files for fresh run

### State Management
- File-based: `.env` files, `.ok` markers, `.json` data, `runs/` log directories, `meraki_memory/`
- No external database for bash scripts — the web UI adds SQLite for job tracking only

---

## Phase 1: Dockerization (Complete)

Single-container image using s6-overlay v3.2.2.0 for process supervision.

### Base Image
- `rockylinux:9.3` (note: 10.1 not yet published on Docker Hub)

### s6 Services (Phase 1)
| Service | Type | Description |
|---------|------|-------------|
| `init-dirs` | oneshot | Create directory structure |
| `init-state` | oneshot | Symlink state into persistent volume |
| `init-env` | oneshot | Bootstrap env files from state |
| `tftpd` | longrun | TFTP server (in.tftpd, UDP 69) |
| `httpd` | longrun | Apache for firmware HTTP serving (port 80) |
| `atd` | longrun | at daemon for scheduled jobs |

### Key Environment Variables
- `CMDS_DOCKER=1` — Signals scripts they're in Docker
- `TZ` — Timezone for scheduling
- `ONLINE_REQUIRED` / `ONLINE_BYPASS_ALLOWED` — GitHub update check control

### Docker Volumes
| Volume | Mount | Purpose |
|--------|-------|---------|
| `cmds2-tftpboot` | `/var/lib/tftpboot` | Firmware images + TFTP data |
| `cmds2-cloud-runs` | `/root/.cloud_admin/runs` | Operation logs |
| `cmds2-hybrid-runs` | `/root/.hybrid_admin/runs` | Hybrid mode logs |
| `cmds2-cloud-state` | `/root/.cloud_admin/state` | Persistent env/markers/memory |
| `cmds2-server-admin` | `/root/.server_admin` | Backup configs, version info |
| `cmds2-at-spool` | `/var/spool/at` | Scheduled job persistence |
| `cmds2-db` | `/var/lib/cmds2` | SQLite database (Phase 2) |

### Networking
- **Production (Linux):** `network_mode: host` required for TFTP UDP port negotiation and direct SSH to switches
- **Development (Docker Desktop):** Port mappings — `8443:8443`, `80:80`, `69:69/udp`

### Helper Scripts
| Script | Path in Container | Purpose |
|--------|-------------------|---------|
| `docker-helpers.sh` | `/usr/local/lib/cmds2/` | `web_progress()` function for JSON progress output |
| `healthcheck.sh` | `/docker-healthcheck.sh` | Health checks for all services |
| `generate-ssl-cert.sh` | `/docker-generate-ssl-cert.sh` | Self-signed TLS cert for nginx |

---

## Phase 2: Web Frontend (Complete)

### Technology Choices
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | React 18 + TypeScript + Vite 6 | Modern SPA, fast HMR |
| UI Library | Ant Design 5 | Enterprise-ready, tables/forms/steps built in |
| Backend | FastAPI + uvicorn | Async Python, OpenAPI docs, WebSocket support |
| Reverse Proxy | nginx (TLS on port 8443) | Serves SPA + proxies API |
| Database | SQLite (aiosqlite) | Zero config, job history + audit log |
| Auth | JWT (httpOnly cookies) | Secure, stateless |
| Real-time | WebSocket | Live progress streaming from bash scripts |

### s6 Services (Phase 2 additions)
| Service | Type | Depends On | Description |
|---------|------|------------|-------------|
| `init-ssl` | oneshot | `init-dirs` | Generate self-signed cert |
| `cmds2-api` | longrun | `init-env` | uvicorn on 127.0.0.1:8000 |
| `nginx` | longrun | `cmds2-api`, `init-ssl` | Reverse proxy on 0.0.0.0:8443 |

### Script Wrapping Pattern
Scripts are wrapped, not rewritten. The bash remains the single source of truth.

```
[Browser] --WebSocket--> [FastAPI] --asyncio.create_subprocess_exec()--> [bash script]
                                   <--stdout line by line (JSON progress)--
```

- `CMDS_WEB_MODE=1` — Triggers `web_progress()` JSON output from bash scripts
- `DIALOG=true` — Suppresses dialog TUI when running via API
- `TERM=dumb` — Prevents ANSI escape sequences
- Output format: `{"pct": 45, "msg": "Probing switch 10.0.1.5..."}`

### Default Credentials
- Username: `admin`
- Password: `changeme`
- Configurable via `CMDS_ADMIN_USER` / `CMDS_ADMIN_PASSWORD` env vars

---

## File Structure

### Backend (`web/backend/`)
```
web/backend/
  requirements.txt          # Python dependencies
  __init__.py
  config.py                 # Settings from CMDS_ env vars
  main.py                   # FastAPI app entry point
  core/
    db.py                   # Async SQLAlchemy + aiosqlite
    env_parser.py           # Read/write bash .env files (masks secrets)
    websocket.py            # ConnectionManager (job-based pub/sub)
    job_manager.py          # In-memory job tracking + dataclass
    script_runner.py        # Async subprocess wrapper + WS streaming
  models/
    database.py             # SQLAlchemy models (JobRecord, AuditLog, UserRecord)
    schemas.py              # Pydantic request/response schemas
  auth/
    jwt.py                  # JWT create/verify + bcrypt password hashing
    router.py               # /api/v1/auth/* (login, refresh, logout, me)
  api/
    status.py               # /api/v1/status (dashboard data)
    cloud/
      setup.py              # /api/v1/cloud/setup (env config, SSH/API tests)
      discovery.py          # /api/v1/cloud/discovery (scan, results, select)
      firmware.py           # /api/v1/cloud/firmware (images, upload, upgrade, schedule)
      preflight.py          # /api/v1/cloud/preflight (run, fix-dns, fix-http, results)
      migration.py          # /api/v1/cloud/migration (start, inventory, network-map)
      ports.py              # /api/v1/cloud/ports (auto, mgmt-ip)
      clean.py              # /api/v1/cloud/clean (preview, start)
    logs/
      router.py             # /api/v1/logs (categories, runs, content, search)
    admin/
      router.py             # /api/v1/admin (services, backup, system-info)
    util/
      router.py             # /api/v1/util (matrix, configs, jobs, cancel)
```

### Frontend (`web/frontend/`)
```
web/frontend/
  package.json              # React 18, antd 5, axios, vite 6, typescript 5.7
  vite.config.ts            # Dev proxy: /api -> localhost:8000
  tsconfig.json
  index.html
  public/cmds2.svg
  src/
    main.tsx                # React entry point
    App.tsx                 # Router + auth guard + ConfigProvider
    types/index.ts          # All TypeScript interfaces
    api/
      client.ts             # Axios + 401 refresh interceptor
      endpoints.ts          # Typed API functions
      websocket.ts          # WsClient with auto-reconnect
    hooks/
      useWebSocket.ts       # useJobProgress() hook
    auth/
      AuthContext.tsx        # Login state context
      LoginPage.tsx          # Ant Design login form
    layouts/
      MainLayout.tsx         # Sidebar nav + header + Outlet
    components/
      JobProgress.tsx        # Real-time progress bar + log terminal
      WorkflowStepper.tsx    # Ant Steps for workflow completion
      LogStream.tsx          # Log viewer with filter/search
    pages/
      Dashboard.tsx          # Service health, device stats, workflow steppers
      Setup.tsx              # Meraki API/SSH config form + test buttons
      Discovery.tsx          # Run scan, results table, device selection
      Firmware.tsx           # Image library, upload, upgrade, scheduling
      Preflight.tsx          # Run checks, fix DNS/HTTP, results table
      Migration.tsx          # Start migration, inventory table
      Ports.tsx              # Auto port + mgmt IP migration
      Clean.tsx              # Preview + confirm file cleanup
      Logs.tsx               # Three-column log browser + search
      Admin.tsx              # Service control, system info, backup, job history
```

### Docker (`docker/`)
```
docker/
  Dockerfile                # Multi-stage: node:20-alpine (frontend) -> rockylinux:9.3
  conf/
    httpd-cmds2.conf        # Apache config for firmware HTTP serving
    nginx-cmds2.conf        # nginx reverse proxy (TLS :8443, proxy to :8000, SPA)
  scripts/
    docker-helpers.sh       # web_progress() bash function
    healthcheck.sh          # Checks tftpd, httpd, atd, API, nginx
    generate-ssl-cert.sh    # Self-signed cert (10yr RSA 2048)
  s6-overlay/s6-rc.d/       # All service definitions
```

---

## Build Issues Resolved

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `rockylinux:10.1` not found | Not published on Docker Hub | Changed to `rockylinux:9.3` |
| `xz: Cannot exec` | Missing in base image | `dnf install xz tar` before s6 extraction |
| `curl-minimal` conflict | Rocky 9.3 ships curl-minimal | `--allowerasing` flag on dnf install |
| s6-rc-compile: invalid type | Windows CRLF line endings | `sed -i 's/\r$//'` on all s6 files |
| `int \| None` TypeError | Python 3.9 lacks union syntax | `eval_type_backport` package + `Optional[]` for SQLAlchemy |
| SQLAlchemy `Mapped[int \| None]` | Runtime type eval ignores `__future__` | Explicit `Optional[int]` in Mapped annotations |
| httpd port 80 conflict | nginx default server also binds :80 | `sed` to remove default server block from nginx.conf |
| passlib bcrypt error | bcrypt 4.1+ dropped `__about__` | Pinned `bcrypt==4.0.1` |
| Auth redirect loop | 401 interceptor did `window.location.href = "/login"` | Removed redirect, let AuthContext handle it |
| Docker Desktop networking | `network_mode: host` is Linux-only | Port mappings for dev, host mode comment for prod |

---

## Modified Bash Scripts

These existing scripts received `web_progress()` instrumentation:

| Script | Progress Points |
|--------|----------------|
| `.cloud_admin/discoverswitches.sh` | During parallel probe completion |
| `.cloud_admin/image_upgrade.sh` | Startup, per-device progress, completion |
| `.cloud_admin/meraki_preflight.sh` | Startup, per-probe progress, completion |
| `.cloud_admin/migration.sh` | Per-device claim progress, completion |
| `.cloud_admin/clean.sh` | Source line only (simple script) |

Pattern added to each:
```bash
[[ "${CMDS_WEB_MODE:-0}" == "1" ]] && . /usr/local/lib/cmds2/docker-helpers.sh 2>/dev/null || true
```

---

## API Endpoints Summary

### Auth (`/api/v1/auth/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Authenticate, set httpOnly cookies |
| POST | `/refresh` | Refresh access token |
| POST | `/logout` | Clear cookies |
| GET | `/me` | Current user info |

### Dashboard (`/api/v1/status/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Services, workflow steps, device counts |

### Cloud Workflow (`/api/v1/cloud/`)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/setup` | Read/write meraki_discovery.env |
| POST | `/setup/test-ssh` | SSH connectivity test |
| POST | `/setup/test-api` | Meraki API key test |
| POST | `/discovery/start` | Launch discoverswitches.sh |
| GET | `/discovery/results` | Read discovery_results.json |
| POST | `/discovery/select` | Save selected devices |
| GET | `/firmware/images` | List firmware images |
| POST | `/firmware/upload` | Upload firmware (streaming) |
| DELETE | `/firmware/images/{name}` | Delete firmware image |
| POST | `/firmware/upgrade` | Launch image_upgrade.sh |
| POST | `/preflight/start` | Launch meraki_preflight.sh |
| POST | `/preflight/fix-dns` | Launch DNS fix |
| POST | `/preflight/fix-http` | Launch HTTP fix |
| GET | `/preflight/results` | Latest preflight CSV |
| POST | `/migration/start` | Launch migration.sh |
| GET | `/migration/inventory` | Read meraki_memory/*.json |
| POST | `/ports/auto` | Auto per-port migration |
| POST | `/ports/mgmt-ip` | Management IP migration |
| GET | `/clean/preview` | Files that would be removed |
| POST | `/clean/start` | Run clean.sh |

### Logs (`/api/v1/logs/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/categories` | Log categories with run counts |
| GET | `/{category}/runs` | Runs within category |
| GET | `/{category}/{run_id}` | Log content |
| GET | `/search` | Cross-log keyword search |

### Admin (`/api/v1/admin/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/services` | List s6 service states |
| POST | `/services/{name}` | Start/stop/restart service |
| POST | `/backup` | Run cmds_backup.sh |
| GET | `/system-info` | Hostname, uptime, disk usage |

### Utility (`/api/v1/util/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/matrix` | cloud_models.json data |
| GET | `/configs` | Backup configs listing |
| GET | `/jobs` | All tracked jobs |
| POST | `/jobs/{id}/cancel` | Cancel running job |

### WebSocket (`/api/v1/ws`)
Subscribe to real-time job updates. Message types: `progress`, `log`, `complete`.

---

## Running Locally

```bash
# Build
docker compose build

# Start
docker compose up -d

# Web UI
# https://localhost:8443  (admin / changeme)

# TUI (original bash interface)
docker exec -it cmds2 bash -c 'cd /root && bash meraki_migration.sh'

# Logs
docker compose logs -f cmds2

# Upload firmware manually
docker cp ./cat9k_iosxe.17.15.01.SPA.bin cmds2:/var/lib/tftpboot/images/
```

---

## Next Steps / Future Work

- [ ] Code-split the React bundle (currently 1.17MB — Vite warns about chunk size)
- [ ] Add hybrid and catalyst-local mode API endpoints (currently cloud-only)
- [ ] Implement firmware upload progress bar in the UI
- [ ] Add WebSocket reconnect indicator in the UI header
- [ ] Write integration tests for API endpoints
- [ ] Add `docker-compose.prod.yml` with `network_mode: host` for Linux deployment
- [ ] HTTPS cert volume mount for user-provided certificates
- [ ] Rate limiting on auth endpoints
- [ ] Audit log UI page
- [ ] Dark mode theme toggle
