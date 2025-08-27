#!/bin/bash

# NEXUS MVP Web UI Startup Script with Virtual Environment
# This script creates a virtual environment, installs dependencies, and starts the web UI

set -e  # Exit on any error

# Configuration
VENV_NAME="nexus-venv"
PORT=${1:-8001}  # Default to port 8001, or use first argument
HOST=${2:-0.0.0.0}  # Default to 0.0.0.0, or use second argument

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 NEXUS MVP Web UI Startup Script${NC}"
echo -e "${BLUE}====================================${NC}"

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}📂 Working directory: $SCRIPT_DIR${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Python 3 is installed
if ! command_exists python3; then
    echo -e "${RED}❌ Error: python3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3.8 or higher${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}🐍 Python version: $PYTHON_VERSION${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_NAME" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment: $VENV_NAME${NC}"
    python3 -m venv "$VENV_NAME"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}📦 Virtual environment already exists: $VENV_NAME${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}🔌 Activating virtual environment${NC}"
source "$VENV_NAME/bin/activate"

# Upgrade pip
echo -e "${YELLOW}📈 Upgrading pip${NC}"
pip install --upgrade pip --quiet

# Check if requirements.txt exists and install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📋 Installing dependencies from requirements.txt${NC}"
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Error: requirements.txt not found${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 Please edit .env file with your AWS credentials:${NC}"
        echo -e "${YELLOW}   - AWS_ACCESS_KEY_ID${NC}"
        echo -e "${YELLOW}   - AWS_SECRET_ACCESS_KEY${NC}"
        echo -e "${YELLOW}   - AWS_REGION${NC}"
    else
        echo -e "${RED}❌ Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Create data directories and generate sample log files
echo -e "${YELLOW}📁 Creating data directories${NC}"
mkdir -p data/logs data/incidents data/knowledge

# Generate sample log files if they don't exist
echo -e "${YELLOW}📊 Checking for sample log files${NC}"
if [ ! -f "data/logs/normal_operations.jsonl" ] || [ ! -f "data/logs/incident_database_connection_timeout.jsonl" ]; then
    echo -e "${YELLOW}🔧 Generating sample log files...${NC}"
    # Set PYTHONPATH to include current directory so imports work
    PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH" python scripts/generate_logs.py 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Could not generate log files automatically${NC}"
        echo -e "${YELLOW}   You can run 'PYTHONPATH=. python scripts/generate_logs.py' manually later${NC}"
    }
    if [ -f "data/logs/normal_operations.jsonl" ]; then
        echo -e "${GREEN}✅ Sample log files generated${NC}"
    fi
else
    echo -e "${GREEN}✅ Sample log files already exist${NC}"
fi

# Check for any processes using the port
if command_exists lsof; then
    EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ ! -z "$EXISTING_PID" ]; then
        echo -e "${YELLOW}⚠️  Port $PORT is already in use by process $EXISTING_PID${NC}"
        echo -e "${YELLOW}🔪 Killing existing process${NC}"
        kill -9 $EXISTING_PID 2>/dev/null || true
        sleep 2
    fi
fi

# Start the web UI
echo -e "${GREEN}🌐 Starting NEXUS MVP Web UI${NC}"
echo -e "${GREEN}   URL: http://localhost:$PORT${NC}"
echo -e "${GREEN}   Host: $HOST${NC}"
echo -e "${GREEN}   Environment: Virtual Environment ($VENV_NAME)${NC}"
echo -e "${YELLOW}───────────────────────────────────────${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${YELLOW}───────────────────────────────────────${NC}"

# Export environment variables for the web app
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Start uvicorn with the web app
python -m uvicorn web.app:app --host "$HOST" --port "$PORT" --reload

# Cleanup message
echo -e "\n${YELLOW}👋 NEXUS MVP Web UI stopped${NC}"
echo -e "${YELLOW}🔌 Virtual environment is still active. Run 'deactivate' to exit.${NC}"
