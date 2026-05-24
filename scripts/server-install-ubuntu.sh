#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '\n==> %s\n' "$1"
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
else
  fail "/etc/os-release not found."
fi

if [[ "${ID:-}" != "ubuntu" ]]; then
  fail "This script is intended for Ubuntu 24.04. Detected ID=${ID:-unknown}."
fi

if [[ "${VERSION_ID:-}" != "24.04" && "${ALLOW_NON_2404:-0}" != "1" ]]; then
  fail "This script is intended for Ubuntu 24.04. Set ALLOW_NON_2404=1 to bypass."
fi

SUDO=""
if [[ "${EUID}" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || fail "sudo is required when running as non-root."
  SUDO="sudo"
fi

log "Installing base packages"
$SUDO apt-get update
$SUDO apt-get install -y ca-certificates curl git gnupg openssl ufw

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  log "Docker and Docker Compose plugin are already installed"
else
  if [[ "${REMOVE_CONFLICTING_DOCKER_PACKAGES:-0}" == "1" ]]; then
    log "Removing conflicting Docker packages"
    for package in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
      $SUDO apt-get remove -y "$package" || true
    done
  fi

  log "Adding official Docker apt repository"
  $SUDO install -m 0755 -d /etc/apt/keyrings
  $SUDO curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  $SUDO chmod a+r /etc/apt/keyrings/docker.asc

  docker_codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-noble}}"
  docker_arch="$(dpkg --print-architecture)"

  cat <<EOF | $SUDO tee /etc/apt/sources.list.d/docker.sources >/dev/null
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${docker_codename}
Components: stable
Architectures: ${docker_arch}
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  log "Installing Docker Engine and Compose plugin"
  $SUDO apt-get update
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

log "Enabling Docker service"
$SUDO systemctl enable --now docker

target_user="${APP_USER:-${SUDO_USER:-}}"
if [[ -n "$target_user" && "$target_user" != "root" ]]; then
  log "Adding user '$target_user' to docker group"
  $SUDO usermod -aG docker "$target_user"
  printf 'User %s was added to docker group. Re-login SSH session before running docker without sudo.\n' "$target_user"
fi

if [[ "${CONFIGURE_FIREWALL:-0}" == "1" ]]; then
  log "Configuring UFW firewall"
  $SUDO ufw allow OpenSSH
  $SUDO ufw allow 80/tcp
  $SUDO ufw allow 443/tcp
  $SUDO ufw --force enable
fi

log "Installed versions"
docker --version || $SUDO docker --version
docker compose version || $SUDO docker compose version
git --version

cat <<'EOF'

Server base installation completed.

Next steps:
1. Re-login SSH session if your user was added to docker group.
2. Copy or clone the project to the server.
3. Create .env from .env.example and fill production secrets.
4. Run: ./scripts/server-deploy.sh

Optional firewall setup:
  CONFIGURE_FIREWALL=1 ./scripts/server-install-ubuntu.sh
EOF
