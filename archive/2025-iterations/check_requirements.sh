#!/bin/bash
# Check that requirements.txt is sorted and has no duplicates

set -e

file="requirements.txt"

if [ ! -f "$file" ]; then
    exit 0
fi

# Check for duplicates
duplicates=$(cut -d'=' -f1 "$file" | sort | uniq -d)
if [ -n "$duplicates" ]; then
    echo "❌ Duplicate packages in requirements.txt:"
    echo "$duplicates"
    exit 1
fi

# Check if sorted (ignore case, ignore version specifiers)
unsorted=$(cut -d'=' -f1 "$file" | sort -f | diff - <(cut -d'=' -f1 "$file") || true)
if [ -n "$unsorted" ]; then
    echo "⚠️  requirements.txt is not sorted alphabetically"
    echo "   Run: sort -f requirements.txt -o requirements.txt"
    # Don't fail, just warn
    exit 0
fi

echo "✅ requirements.txt looks good"
exit 0
