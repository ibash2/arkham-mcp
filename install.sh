#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/ibash2/arkham-mcp"
INSTALL_DIR="${HOME}/.local/share/arkham-mcp"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; RESET='\033[0m'
info()  { echo -e "${CYAN}▶ $*${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
err()   { echo -e "${RED}✗ $*${RESET}" >&2; }

if ! command -v git &>/dev/null; then
  err "git is required but not installed."
  echo "  Install it from https://git-scm.com and re-run this script."
  exit 1
fi

if ! command -v uv &>/dev/null; then
  info "uv not found — installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
  if ! command -v uv &>/dev/null; then
    err "uv install succeeded but it is not in PATH."
    echo "  Open a new terminal and re-run this script."
    exit 1
  fi
  ok "uv installed"
fi

if [ -d "${INSTALL_DIR}/.git" ]; then
  info "Updating existing install at ${INSTALL_DIR}..."
  git -C "${INSTALL_DIR}" pull --ff-only
else
  info "Cloning arkham-mcp into ${INSTALL_DIR}..."
  git clone "${REPO_URL}" "${INSTALL_DIR}"
fi
ok "Repository ready"

info "Installing dependencies..."
uv sync --project "${INSTALL_DIR}" --quiet
ok "Dependencies installed"

info "Launching installer..."
uv run --project "${INSTALL_DIR}" python "${INSTALL_DIR}/installer/install.py"
