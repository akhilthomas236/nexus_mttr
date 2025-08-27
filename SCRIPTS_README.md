# NEXUS MVP - Virtual Environment Scripts

This directory contains scripts to run the NEXUS MVP Web UI in a clean virtual environment.

## Quick Start

```bash
# Start the web UI (creates virtual environment automatically)
./start_web_ui.sh

# Or use the management script
./manage.sh start
```

## Scripts

### 1. `start_web_ui.sh` - Direct Startup Script
- Creates virtual environment if it doesn't exist
- Installs dependencies from requirements.txt
- Sets up .env file from .env.example if needed
- Creates data directories
- Starts the web UI with uvicorn

**Usage:**
```bash
./start_web_ui.sh [PORT] [HOST]

# Examples:
./start_web_ui.sh                # Default: port 8001, host 0.0.0.0
./start_web_ui.sh 8080           # Custom port
./start_web_ui.sh 8080 127.0.0.1 # Custom port and host
```

### 2. `manage.sh` - Management Script
Provides comprehensive management of the web UI and virtual environment.

**Commands:**
- `./manage.sh start [PORT] [HOST]` - Start the web UI
- `./manage.sh stop [PORT]` - Stop the web UI
- `./manage.sh restart [PORT]` - Restart the web UI
- `./manage.sh status [PORT]` - Check if web UI is running
- `./manage.sh shell` - Activate virtual environment shell
- `./manage.sh clean` - Remove virtual environment
- `./manage.sh install` - Install/update dependencies
- `./manage.sh logs` - Show recent logs

**Examples:**
```bash
# Start on default port
./manage.sh start

# Start on custom port
./manage.sh start 8080

# Check status
./manage.sh status

# Enter virtual environment shell
./manage.sh shell

# Stop the server
./manage.sh stop

# Clean reinstall
./manage.sh clean
./manage.sh start
```

## Environment Setup

### Prerequisites
- Python 3.8 or higher
- `python3-venv` package (usually included with Python)

### AWS Configuration
1. Copy `.env.example` to `.env` (done automatically)
2. Edit `.env` with your AWS credentials:
   ```bash
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=us-east-1
   ```

## Virtual Environment Details

- **Location**: `nexus-venv/` directory
- **Python Version**: Uses system Python 3
- **Dependencies**: Installed from `requirements.txt`
- **Isolation**: Completely isolated from system Python packages

## Troubleshooting

### Port Already in Use
The scripts automatically detect and kill processes using the target port.

### Permission Errors
Make sure scripts are executable:
```bash
chmod +x start_web_ui.sh manage.sh
```

### Python Version Issues
Ensure Python 3.8+ is installed:
```bash
python3 --version
```

### Virtual Environment Issues
Clean and recreate:
```bash
./manage.sh clean
./manage.sh start
```

### Dependencies Issues
Reinstall dependencies:
```bash
./manage.sh install
```

## Development Workflow

1. **Start Development Server:**
   ```bash
   ./manage.sh start
   ```

2. **Enter Shell for Development:**
   ```bash
   ./manage.sh shell
   # Now you're in the virtual environment
   python -m uvicorn web.app:app --reload --port 8001
   ```

3. **Check Status:**
   ```bash
   ./manage.sh status
   ```

4. **View Logs:**
   ```bash
   ./manage.sh logs
   ```

5. **Stop When Done:**
   ```bash
   ./manage.sh stop
   ```

## Production Deployment

For production, consider:
- Using `gunicorn` instead of `uvicorn` for better performance
- Setting up systemd service files
- Using nginx as a reverse proxy
- Configuring proper logging and monitoring

Example production command:
```bash
source nexus-venv/bin/activate
gunicorn web.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
