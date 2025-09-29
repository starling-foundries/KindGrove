#!/bin/bash
# Quick launcher for mangrove workflow notebook

echo "🌿 Mangrove Workflow Notebook Launcher"
echo "======================================"
echo ""

# Check if Jupyter is installed
if ! command -v jupyter &> /dev/null; then
    echo "❌ Jupyter not found. Install with:"
    echo "   pip install jupyter jupyterlab"
    exit 1
fi

# Check if already running
if jupyter lab list 2>/dev/null | grep -q "http://localhost:8890"; then
    echo "✅ Jupyter Lab already running at http://localhost:8890"
    echo ""
    echo "Opening notebook in browser..."
    sleep 2
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:8890/lab/tree/mangrove_workflow.ipynb"
    else
        xdg-open "http://localhost:8890/lab/tree/mangrove_workflow.ipynb" 2>/dev/null || \
        echo "📋 Navigate to: http://localhost:8890/lab/tree/mangrove_workflow.ipynb"
    fi
else
    echo "🚀 Starting Jupyter Lab..."
    echo ""
    echo "📍 Notebook will open automatically"
    echo "🛑 Press Ctrl+C to stop the server"
    echo ""

    # Start Jupyter Lab directly on the notebook
    jupyter lab mangrove_workflow.ipynb --port=8890
fi