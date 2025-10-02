#!/bin/bash

# Globridge MVP Server Startup Script
echo "🚀 Starting Globridge MVP Server..."

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the globridge_mvp directory"
    exit 1
fi

# Check if Python dependencies are installed
echo "📦 Checking dependencies..."
python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "🌟 Starting server on http://localhost:8000"
echo "📱 Frontend will be available at: http://localhost:8000"
echo "🔧 API endpoints available at: http://localhost:8000/api/*"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
