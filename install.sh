#!/usr/bin/env bash
set -e

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "${INSTALL_DIR}"

SCRIPT_URL="https://raw.githubusercontent.com/shoryasrivastava388-sys/qwen-agent/main/qwen_agent.py"
TARGET="${INSTALL_DIR}/qwen-agent"

echo "→ Installing qwen-agent to ${INSTALL_DIR}..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${SCRIPT_URL}" -o "${TARGET}"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "${TARGET}" "${SCRIPT_URL}"
else
    echo "Error: curl or wget is required."
    exit 1
fi

chmod +x "${TARGET}"
ln -sf "${TARGET}" "${INSTALL_DIR}/qc"

echo "✓ Successfully installed qwen-agent and qc to ${INSTALL_DIR}"
echo ""
echo "Make sure ${INSTALL_DIR} is in your PATH:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "Usage:"
echo "  qc                 # Interactive mode"
echo "  qc -y 'Task'       # Auto-approve mode"
