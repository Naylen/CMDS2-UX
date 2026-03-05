#!/bin/bash
# Docker HEALTHCHECK script for CMDS2 container
# Verifies that all critical services are running.

set -e

# Check TFTP daemon
pgrep -f 'in.tftpd' > /dev/null 2>&1 || { echo "TFTP not running"; exit 1; }

# Check Apache httpd
pgrep -f 'httpd' > /dev/null 2>&1 || { echo "httpd not running"; exit 1; }

# Check at daemon
pgrep -f 'atd' > /dev/null 2>&1 || { echo "atd not running"; exit 1; }

# Check HTTP responsiveness (firmware serving via Apache)
curl -sf --max-time 5 http://localhost/images/ > /dev/null 2>&1 || { echo "HTTP not responding"; exit 1; }

# Phase 2: Check API health
curl -sf --max-time 5 http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1 || { echo "API not responding"; exit 1; }

# Phase 2: Check nginx
pgrep -f 'nginx' > /dev/null 2>&1 || { echo "nginx not running"; exit 1; }

exit 0
