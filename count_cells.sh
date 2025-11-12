#!/usr/bin/env bash
# Count cells per category for a factor in an h5ad file
# Usage: ./count_cells.sh <h5ad_file> <factor_name>

set -euo pipefail

if [ $# -ne 2 ]; then
    echo "Usage: $0 <h5ad_file> <factor_name>" >&2
    echo "Example: $0 data.h5ad sample" >&2
    exit 1
fi

H5AD_FILE="$1"
FACTOR_NAME="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if file exists
if [ ! -f "$H5AD_FILE" ]; then
    echo "Error: File not found: $H5AD_FILE" >&2
    exit 1
fi

# Get categories into an array (portable way)
i=0
declare -a cat_array
while IFS= read -r line; do
    cat_array[$i]="$line"
    i=$((i + 1))
done < <("${SCRIPT_DIR}/extract_categories.sh" "$H5AD_FILE" "$FACTOR_NAME")

# Extract codes and count frequencies
codes=$(h5dump -d "/obs/${FACTOR_NAME}/codes" "$H5AD_FILE" 2>/dev/null | \
    grep -oE "[0-9]+" | \
    sort -n | \
    uniq -c | \
    awk '{print $2":"$1}')

# Map codes to category names and output
while IFS=: read -r code count; do
    if [ "$code" -lt "${#cat_array[@]}" ]; then
        echo "${cat_array[$code]}:$count"
    fi
done <<< "$codes"
