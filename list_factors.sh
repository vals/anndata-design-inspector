#!/usr/bin/env bash
# List all categorical factors (Groups) in the obs section
# Usage: ./list_factors.sh <h5ad_file>

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <h5ad_file>" >&2
    echo "Example: $0 data.h5ad" >&2
    exit 1
fi

H5AD_FILE="$1"

# Check if file exists
if [ ! -f "$H5AD_FILE" ]; then
    echo "Error: File not found: $H5AD_FILE" >&2
    exit 1
fi

# List obs contents and filter for Groups
h5ls "$H5AD_FILE/obs" 2>/dev/null | \
    grep "Group$" | \
    awk '{print $1}' | \
    sort
