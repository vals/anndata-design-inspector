#!/usr/bin/env bash
# Detect if factor B is nested within factor A using name pattern analysis
# Usage: ./detect_nesting.sh <h5ad_file> <factor_a> <factor_b>
# Returns: "nested" if B is nested in A, "crossed" otherwise

set -euo pipefail

if [ $# -ne 3 ]; then
    echo "Usage: $0 <h5ad_file> <factor_a> <factor_b>" >&2
    echo "Example: $0 data.h5ad genotype sample" >&2
    exit 1
fi

H5AD_FILE="$1"
FACTOR_A="$2"
FACTOR_B="$3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get categories for both factors
categories_a=$("${SCRIPT_DIR}/extract_categories.sh" "$H5AD_FILE" "$FACTOR_A")
categories_b=$("${SCRIPT_DIR}/extract_categories.sh" "$H5AD_FILE" "$FACTOR_B")

# Check if factor B names contain factor A names
nested_count=0
total_b=0

while IFS= read -r cat_b; do
    [ -z "$cat_b" ] && continue
    total_b=$((total_b + 1))

    # Check if this B category contains any A category name
    while IFS= read -r cat_a; do
        [ -z "$cat_a" ] && continue

        # Case-insensitive substring match
        if echo "$cat_b" | grep -qi "$cat_a"; then
            nested_count=$((nested_count + 1))
            break
        fi
    done <<< "$categories_a"
done <<< "$categories_b"

# If most (>50%) of B categories contain A names, it's nested
if [ $total_b -gt 0 ] && [ $nested_count -gt $((total_b / 2)) ]; then
    echo "nested"
else
    echo "crossed"
fi
