#!/usr/bin/env bash
set -e

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "${INSTALL_DIR}"

SCRIPT_URL="https://raw.githubusercontent.com/shoryasrivastava388-sys/local-code/main/local_code.py"
TARGET="${INSTALL_DIR}/local-code"

echo "→ Installing local-code (lc) to ${INSTALL_DIR}..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${SCRIPT_URL}" -o "${TARGET}"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "${TARGET}" "${SCRIPT_URL}"
else
    echo "Error: curl or wget is required."
    exit 1
fi

chmod +x "${TARGET}"
ln -sf "${TARGET}" "${INSTALL_DIR}/lc"
ln -sf "${TARGET}" "${INSTALL_DIR}/qc"
ln -sf "${TARGET}" "${INSTALL_DIR}/qwen-agent"

echo "✓ Successfully installed local-code (lc) to ${INSTALL_DIR}"
echo ""
echo "Make sure ${INSTALL_DIR} is in your PATH:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo ""
echo "Usage:"
echo "  lc                 # Interactive mode"
echo "  lc -y 'Task'       # Auto-approve mode"

