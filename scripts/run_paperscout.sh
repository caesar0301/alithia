#!/bin/bash
# Run PaperScout agent with configuration from environment variable or file
#
# Usage:
#   ./scripts/run_paperscout.sh
#   ./scripts/run_paperscout.sh --from-date 2024-01-01 --to-date 2024-01-07
#
# Environment variables:
#   ALITHIA_CONFIG_JSON: JSON configuration string (required if CONFIG_FILE not set)
#   CONFIG_FILE: Path to configuration file (optional, overrides ALITHIA_CONFIG_JSON)

set -e

CONFIG_FILE="${CONFIG_FILE:-paperscout_config.json}"
ARGS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --from-date)
            ARGS+=("--from-date" "$2")
            shift 2
            ;;
        --to-date)
            ARGS+=("--to-date" "$2")
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Handle configuration
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    echo "📄 Using existing configuration file: $CONFIG_FILE"
    CONFIG_ARG="--config $CONFIG_FILE"
elif [ -n "$ALITHIA_CONFIG_JSON" ]; then
    echo "📄 Creating configuration file from ALITHIA_CONFIG_JSON..."
    echo "$ALITHIA_CONFIG_JSON" > "$CONFIG_FILE"
    CONFIG_ARG="--config $CONFIG_FILE"
    # Clean up config file on exit
    trap "rm -f $CONFIG_FILE" EXIT
else
    echo "⚠️  No configuration provided, using default settings"
    CONFIG_ARG=""
fi

# Run PaperScout agent
echo "🚀 Running PaperScout agent..."
uv run python -m alithia.run paperscout_agent $CONFIG_ARG "${ARGS[@]}"

echo "✅ PaperScout agent completed successfully"

