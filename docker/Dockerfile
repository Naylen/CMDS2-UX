###############################################################################
# CMDS2 — Catalyst-to-Meraki Deployment Server (Dockerized)
#
# Single-container image with s6-overlay for process supervision.
# Phase 1: TFTP (in.tftpd), Apache httpd, atd (scheduled jobs)
# Phase 2: FastAPI backend (uvicorn), React frontend (nginx on :8443)
#
# Usage:
#   docker compose up -d
#   docker exec -it cmds2 bash -c 'cd /root && bash meraki_migration.sh'
#   Web UI: https://<host>:8443
###############################################################################

# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install
COPY web/frontend/ ./
RUN npm run build

# ── Stage 2: Production image ─────────────────────────────────────────────

FROM rockylinux/rockylinux:10.1

ARG S6_OVERLAY_VERSION=3.2.2.0
ARG TARGETARCH

LABEL maintainer="CMDS2 Project"
LABEL description="Catalyst-to-Meraki Deployment Server"

# ---------------------------------------------------------------------------
# Layer 1: s6-overlay init system
# ---------------------------------------------------------------------------
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp/
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp/s6-overlay-x86_64.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-aarch64.tar.xz /tmp/s6-overlay-aarch64.tar.xz

RUN dnf -y install xz tar && dnf clean all && \
    set -eux; \
    case "${TARGETARCH:-$(uname -m)}" in \
      amd64|x86_64)  ARCH=x86_64 ;; \
      arm64|aarch64) ARCH=aarch64 ;; \
      *)             echo "Unsupported arch: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz; \
    tar -C / -Jxpf /tmp/s6-overlay-${ARCH}.tar.xz; \
    rm -f /tmp/s6-overlay-*.tar.xz

# ---------------------------------------------------------------------------
# Layer 2: System packages (heaviest layer — cached aggressively)
# ---------------------------------------------------------------------------
RUN dnf -y install epel-release && \
    dnf config-manager --set-enabled crb && \
    dnf -y makecache --refresh && \
    dnf -y install \
      dialog \
      expect \
      tar \
      nmap \
      at \
      bc \
      rsync \
      sshpass \
      openssh-clients \
      fail2ban \
      tftp-server \
      net-tools \
      dmidecode \
      ipcalc \
      bind-utils \
      curl \
      wget \
      git \
      httpd \
      python3 \
      python3-pip \
      pv \
      jq \
      util-linux \
      procps-ng \
      hostname \
      nano \
      zip \
      gzip \
      nginx \
      openssl \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# ---------------------------------------------------------------------------
# Layer 3: Python packages
# ---------------------------------------------------------------------------
COPY web/backend/requirements.txt /tmp/requirements-web.txt
RUN python3 -m pip install --no-cache-dir --break-system-packages \
      --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir --break-system-packages meraki && \
    python3 -m pip install --no-cache-dir --break-system-packages \
      -r /tmp/requirements-web.txt && \
    rm -f /tmp/requirements-web.txt

# ---------------------------------------------------------------------------
# Layer 4: TFTP directory structure + Apache config
# ---------------------------------------------------------------------------
RUN mkdir -p /var/lib/tftpboot/images \
             /var/lib/tftpboot/hybrid \
             /var/lib/tftpboot/wlc \
             /var/lib/tftpboot/mig \
             /var/lib/tftpboot/cat && \
    chmod -R 777 /var/lib/tftpboot && \
    # Symlink for Cockpit/manual upload convenience
    ln -sfn /var/lib/tftpboot/images /root/IOS-XE_images

# ---------------------------------------------------------------------------
# Layer 5: CMDS2 application code
# ---------------------------------------------------------------------------
COPY .cloud_admin/   /root/.cloud_admin/
COPY .hybrid_admin/  /root/.hybrid_admin/
COPY .cat_admin/     /root/.cat_admin/
COPY .server_admin/  /root/.server_admin/
COPY meraki_migration.sh /root/meraki_migration.sh
COPY updates/        /root/updates/

# Ensure all scripts are executable
RUN find /root/.cloud_admin /root/.hybrid_admin /root/.cat_admin /root/.server_admin \
      -name '*.sh' -exec chmod +x {} + && \
    chmod +x /root/meraki_migration.sh

# ---------------------------------------------------------------------------
# Layer 6: Docker helper scripts
# ---------------------------------------------------------------------------
COPY docker/scripts/docker-helpers.sh  /usr/local/lib/cmds2/docker-helpers.sh
COPY docker/scripts/healthcheck.sh     /docker-healthcheck.sh
COPY docker/scripts/generate-ssl-cert.sh /docker-generate-ssl-cert.sh
RUN sed -i 's/\r$//' /usr/local/lib/cmds2/docker-helpers.sh /docker-healthcheck.sh /docker-generate-ssl-cert.sh && \
    chmod +x /docker-healthcheck.sh /docker-generate-ssl-cert.sh

# ---------------------------------------------------------------------------
# Layer 7: Apache config for firmware HTTP serving
# ---------------------------------------------------------------------------
COPY docker/conf/httpd-cmds2.conf /etc/httpd/conf.d/cmds2.conf
COPY docker/conf/nginx-cmds2.conf /etc/nginx/conf.d/cmds2.conf
# Disable default welcome/server pages and nginx default port-80 server
RUN rm -f /etc/httpd/conf.d/welcome.conf 2>/dev/null; true && \
    rm -f /etc/nginx/conf.d/default.conf 2>/dev/null; true && \
    sed -i '/^    server {/,/^    }/d' /etc/nginx/nginx.conf

# ---------------------------------------------------------------------------
# Layer 8: s6 service definitions
# ---------------------------------------------------------------------------
COPY docker/s6-overlay/s6-rc.d/ /etc/s6-overlay/s6-rc.d/

# Fix Windows CRLF line endings and ensure scripts are executable
RUN find /etc/s6-overlay/s6-rc.d -type f -exec sed -i 's/\r$//' {} + && \
    find /etc/s6-overlay/s6-rc.d -name 'run' -exec chmod +x {} + && \
    find /etc/s6-overlay/s6-rc.d -name 'up' -exec chmod +x {} +

# ---------------------------------------------------------------------------
# Layer 9: Phase 2 — Web backend + frontend
# ---------------------------------------------------------------------------
COPY web/backend/ /root/web/backend/

# Copy pre-built React frontend from build stage
COPY --from=frontend-build /build/dist/ /var/www/cmds2/

# ---------------------------------------------------------------------------
# Layer 10: State directory structure
#   /root/.cloud_admin/state/ is the persistent volume mount point.
#   init-state creates symlinks from expected paths into this volume.
# ---------------------------------------------------------------------------
RUN mkdir -p /root/.cloud_admin/state \
             /root/.cloud_admin/state/meraki_memory \
             /root/.cloud_admin/state/schedules \
             /root/.cloud_admin/state/uplink_types && \
    mkdir -p /root/.hybrid_admin/state && \
    mkdir -p /var/lib/cmds2 && \
    mkdir -p /var/spool/at

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ENV CMDS_DOCKER=1
ENV S6_KEEP_ENV=1
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=30000
ENV LANG=C
ENV LC_ALL=C

# ---------------------------------------------------------------------------
# Entrypoint (s6-overlay init)
# ---------------------------------------------------------------------------
ENTRYPOINT ["/init"]
