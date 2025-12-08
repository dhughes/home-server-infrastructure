#!/bin/bash
#
# Infrastructure deploy script
# This script is allowed to run with passwordless sudo (see /etc/sudoers.d/infrastructure)
#
# Usage:
#   ./deploy.sh          - Deploy everything (caddy + all services)
#   ./deploy.sh caddy    - Deploy only Caddy config
#   ./deploy.sh auth     - Deploy only auth service
#   ./deploy.sh services - Deploy all services (not caddy)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

deploy_caddy() {
    echo "Generating Caddyfile from app configs..."
    python3 "$SCRIPT_DIR/generate-caddyfile.py"
    echo "Deploying Caddy config..."
    cp "$SCRIPT_DIR/caddy/Caddyfile" /etc/caddy/Caddyfile
    systemctl restart caddy
    echo "Caddy deployed and restarted."
}

deploy_auth() {
    echo "Deploying auth service..."
    systemctl restart auth
    echo "Auth service restarted."
}

deploy_services() {
    deploy_auth
    # Add more services here as needed
}

deploy_all() {
    deploy_caddy
    deploy_services
}

case "${1:-all}" in
    caddy)
        deploy_caddy
        ;;
    auth)
        deploy_auth
        ;;
    services)
        deploy_services
        ;;
    all)
        deploy_all
        ;;
    *)
        echo "Unknown target: $1"
        echo "Usage: $0 [caddy|auth|services|all]"
        exit 1
        ;;
esac

echo "Deploy complete."
