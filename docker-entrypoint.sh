#!/bin/bash
set -e

# Initialize .env files if not already done
if [ ! -f "/app/skills/sci-search/.env" ]; then
    echo "[Aut_Sci_Write] Initializing per-skill .env files..."
    node /app/init-env.js
fi

# Check if API keys are configured
echo "[Aut_Sci_Write] Configuration status:"

check_env_file() {
    local skill=$1
    local key=$2
    local file="/app/skills/${skill}/.env"

    if [ -f "$file" ] && grep -q "^${key}=.\+" "$file"; then
        echo "  ✓ ${skill}: ${key} configured"
    else
        echo "  ✗ ${skill}: ${key} not configured (optional)"
    fi
}

check_env_file "sci-search" "WOS_API_KEY"
check_env_file "sci-zotero" "ZOTERO_API_KEY"
check_env_file "sci-ppt" "ANTHROPIC_API_KEY"

echo ""
echo "[Aut_Sci_Write] Container ready."
echo "  Working directory: /app"
echo "  Data directory: /data (mounted from ./data)"
echo ""
echo "Example commands:"
echo "  python scripts/extract_core_insights.py /data/paper.pdf"
echo "  python scripts/zotero.py list"
echo ""

# Execute the command passed to the container
exec "$@"
