#!/usr/bin/env bash
# Extract category names from a categorical factor in an h5ad file
# Usage: ./extract_categories.sh <h5ad_file> <factor_name>

set -euo pipefail

if [ $# -ne 2 ]; then
    echo "Usage: $0 <h5ad_file> <factor_name>" >&2
    echo "Example: $0 data.h5ad genotype" >&2
    exit 1
fi

H5AD_FILE="$1"
FACTOR_NAME="$2"

# Check if file exists
if [ ! -f "$H5AD_FILE" ]; then
    echo "Error: File not found: $H5AD_FILE" >&2
    exit 1
fi

# Extract categories and clean up output
h5dump -d "/obs/${FACTOR_NAME}/categories" "$H5AD_FILE" 2>/dev/null | \
    awk '/^   DATA \{/{flag=1; next} /^   \}/ && flag{exit} flag' | \
    sed 's/^[[:space:]]*([0-9]*):[[:space:]]*//' | \
    tr -d '"' | \
    tr ',' '\n' | \
    sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
    grep -v '^$'
