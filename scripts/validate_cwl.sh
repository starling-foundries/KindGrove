#!/bin/bash
# Validate CWL workflow syntax using cwltool

set -e

# Check if cwltool is available
if ! command -v cwltool &> /dev/null; then
    echo "⚠️  cwltool not found - skipping CWL validation"
    echo "   Install with: pip install cwltool"
    exit 0  # Don't block commit if tool not installed
fi

# Validate each CWL file passed as argument
exitcode=0
for file in "$@"; do
    echo "Validating CWL: $file"
    if ! cwltool --validate "$file" > /dev/null 2>&1; then
        echo "❌ CWL validation failed for: $file"
        cwltool --validate "$file"
        exitcode=1
    else
        echo "✅ Valid CWL: $file"
    fi
done

exit $exitcode
