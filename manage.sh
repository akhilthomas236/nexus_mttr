#!/bin/bash

# NEXUS MVP Web UI Management Script
# This script helps manage the virtual environment and web UI processes

set -e

# Configuration
VENV_NAME="nexus-venv"
DEFAULT_PORT=8001

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to show usage
show_usage() {
    echo -e "${BLUE}NEXUS MVP Web UI Management${NC}"
    echo -e "${BLUE}===========================${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [PORT] [HOST]  Start the web UI (default: port 8001, host 0.0.0.0)"
    echo "  stop                 Stop the web UI"
    echo "  restart [PORT]       Restart the web UI"
    echo "  status               Check if web UI is running"
    echo "  shell                Activate virtual environment shell"
    echo "  clean                Remove virtual environment"
    echo "  install              Install/update dependencies"
    echo "  logs                 Show recent logs"
    echo ""
    echo "Examples:"
    echo "  $0 start             # Start on default port 8001"
    echo "  $0 start 8080        # Start on port 8080"
    echo "  $0 stop              # Stop the web UI"
    echo "  $0 shell             # Enter virtual environment"
}

# Function to check if process is running on port
check_port() {
    local port=${1:-$DEFAULT_PORT}
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:$port 2>/dev/null || true
    else
        # Fallback for systems without lsof
        netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 || true
    fi
}

# Function to stop web UI
stop_web_ui() {
    local port=${1:-$DEFAULT_PORT}
    local pid=$(check_port $port)
    
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}🔪 Stopping process on port $port (PID: $pid)${NC}"
        kill -TERM $pid 2>/dev/null || true
        sleep 2
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}🔨 Force killing process${NC}"
            kill -9 $pid 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ Web UI stopped${NC}"
    else
        echo -e "${YELLOW}ℹ️  No process found on port $port${NC}"
    fi
}

# Function to get status
get_status() {
    local port=${1:-$DEFAULT_PORT}
    local pid=$(check_port $port)
    
    if [ ! -z "$pid" ]; then
        echo -e "${GREEN}✅ NEXUS Web UI is running${NC}"
        echo -e "${GREEN}   Port: $port${NC}"
        echo -e "${GREEN}   PID: $pid${NC}"
        echo -e "${GREEN}   URL: http://localhost:$port${NC}"
        
        # Try to get process info
        if command -v ps >/dev/null 2>&1; then
            echo -e "${YELLOW}   Process: $(ps -p $pid -o comm= 2>/dev/null || echo 'Unknown')${NC}"
        fi
    else
        echo -e "${RED}❌ NEXUS Web UI is not running on port $port${NC}"
    fi
}

# Function to activate shell
activate_shell() {
    if [ -d "$VENV_NAME" ]; then
        echo -e "${GREEN}🐚 Activating virtual environment shell${NC}"
        echo -e "${YELLOW}💡 Use 'deactivate' to exit the virtual environment${NC}"
        echo -e "${YELLOW}💡 Use 'python -m uvicorn web.app:app --reload' to start the server manually${NC}"
        exec bash --rcfile <(echo "source $VENV_NAME/bin/activate; PS1='(nexus-venv) \[\033[1;32m\]\u@\h:\w\[\033[0m\]\$ '")
    else
        echo -e "${RED}❌ Virtual environment not found. Run './start_web_ui.sh' first.${NC}"
        exit 1
    fi
}

# Function to clean virtual environment
clean_venv() {
    stop_web_ui
    
    if [ -d "$VENV_NAME" ]; then
        echo -e "${YELLOW}🧹 Removing virtual environment: $VENV_NAME${NC}"
        rm -rf "$VENV_NAME"
        echo -e "${GREEN}✅ Virtual environment removed${NC}"
    else
        echo -e "${YELLOW}ℹ️  Virtual environment not found${NC}"
    fi
}

# Function to install dependencies
install_deps() {
    if [ ! -d "$VENV_NAME" ]; then
        echo -e "${YELLOW}📦 Creating virtual environment${NC}"
        python3 -m venv "$VENV_NAME"
    fi
    
    echo -e "${YELLOW}🔌 Activating virtual environment${NC}"
    source "$VENV_NAME/bin/activate"
    
    echo -e "${YELLOW}📈 Upgrading pip${NC}"
    pip install --upgrade pip --quiet
    
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}📋 Installing dependencies${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    if [ -f "nexus-mvp.log" ]; then
        echo -e "${YELLOW}📄 Recent logs from nexus-mvp.log:${NC}"
        tail -50 nexus-mvp.log
    else
        echo -e "${YELLOW}ℹ️  No log file found${NC}"
    fi
}

# Main script logic
case "${1:-help}" in
    "start")
        PORT=${2:-$DEFAULT_PORT}
        HOST=${3:-0.0.0.0}
        echo -e "${BLUE}🚀 Starting NEXUS Web UI on port $PORT${NC}"
        exec ./start_web_ui.sh $PORT $HOST
        ;;
    
    "stop")
        PORT=${2:-$DEFAULT_PORT}
        stop_web_ui $PORT
        ;;
    
    "restart")
        PORT=${2:-$DEFAULT_PORT}
        HOST=${3:-0.0.0.0}
        echo -e "${BLUE}🔄 Restarting NEXUS Web UI${NC}"
        stop_web_ui $PORT
        sleep 1
        exec ./start_web_ui.sh $PORT $HOST
        ;;
    
    "status")
        PORT=${2:-$DEFAULT_PORT}
        get_status $PORT
        ;;
    
    "shell")
        activate_shell
        ;;
    
    "clean")
        clean_venv
        ;;
    
    "install")
        install_deps
        ;;
    
    "logs")
        show_logs
        ;;
    
    "help"|*)
        show_usage
        ;;
esac
