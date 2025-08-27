# NEXUS MVP - AI-Powered Incident Response System

A simplified implementation demonstrating the core concepts of the NEXUS platform for reducing Mean Time To Repair (MTTR) through agentic AI **powered by Amazon Bedrock**.

## Overview

This MVP demonstrates:
- **Log Generation**: Simulated system logs and metrics
- **MCP Agents**: Simplified agent framework for incident response
- **AI Analysis**: Amazon Bedrock-powered root cause analysis with pattern-based fallback
- **Web Interface**: Simple dashboard for monitoring incidents
- **Automation**: AI-generated remediation script and runbook generation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXUS MVP                                │
├─────────────────────────────────────────────────────────────┤
│  Web Dashboard (FastAPI + HTML)                            │
├─────────────────────────────────────────────────────────────┤
│  MCP Agents                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ Log Ingester│ │  Analyzer   │ │    Remediation          │ │
│  │   Agent     │ │   Agent     │ │      Agent              │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │   Logs      │ │  Incidents  │ │      Knowledge          │ │
│  │(JSON Files) │ │ (SQLite)    │ │     (JSON)              │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.8+
- AWS Account with Bedrock access (optional - fallback mode available)

### Option 1: Easy Setup with Bedrock (Recommended)
```bash
# 1. Set up AWS credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key  
export AWS_REGION=us-east-1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify Bedrock setup
python scripts/setup_bedrock.py

# 4. Run the interactive startup script
python start.py
```

### Option 2: Easy Setup (Fallback Mode)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the interactive startup script
python start.py
```

### Option 2: Manual Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Full Demo**:
   ```bash
   python scripts/run_mvp.py --mode demo
   ```

3. **Access Dashboard**:
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Option 3: Individual Components
```bash
# Generate sample logs
python scripts/generate_logs.py

# Run agents only
python scripts/run_mvp.py --mode agents-only

# Run web interface only
python scripts/run_mvp.py --mode web-only

# Run tests
python scripts/test_agents.py
```

## Features Demonstrated

### 1. Log Generation
- Simulated application logs with realistic failure patterns
- Multiple service types (API, Database, Cache, Queue)
- Time-series metrics with anomalies
- Error injection for testing scenarios

### 2. MCP Agent Framework
- Agent registration and discovery
- Message passing between agents
- Event-driven processing
- Health monitoring

### 3. Incident Detection & Analysis
- Automatic incident detection from log patterns
- Root cause hypothesis generation
- Confidence scoring
- Evidence collection

### 4. Remediation Planning
- Automated runbook generation
- Risk assessment
- Validation steps
- Script templates

## File Structure

```
nexus-mvp/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── main.py                  # Main application entry point
```
nexus-mvp/
├── README.md                 # This file
├── requirements.txt          # Python dependencies  
├── start.py                 # Interactive startup script
├── config.py                # Configuration settings
├── agents/                  # MCP Agent implementations
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class
│   ├── log_ingester.py      # Log collection agent
│   ├── analyzer.py          # Analysis agent
│   └── remediation.py       # Remediation agent
├── models/                  # Data models
│   └── __init__.py          # All data models (LogEntry, Incident, etc.)
├── messaging/               # Inter-agent communication
│   ├── __init__.py
│   └── message_bus.py       # Message bus and agent registry
├── web/                     # Web interface
│   ├── __init__.py
│   ├── app.py              # FastAPI application with dashboard
│   └── static/             # Static files (created automatically)
├── scripts/                # Utility scripts
│   ├── generate_logs.py    # Log generation
│   ├── run_mvp.py          # Main application runner
│   └── test_agents.py      # Agent testing suite
├── data/                   # Generated data (created on first run)
│   └── logs/               # Generated log files
└── tests/                  # Additional test files (future)
```

## Components Overview

### 🤖 Agents
- **Log Ingester Agent**: Processes log files, detects anomalies, generates summaries
- **Analyzer Agent**: Detects incidents, performs root cause analysis, assesses impact
- **Remediation Agent**: Generates remediation plans, runbooks, and automation scripts

### 🌐 Web Interface  
- **Dashboard**: Real-time view of system health and active incidents
- **REST API**: Full API for incident management and agent control
- **Interactive UI**: Modern web interface with auto-refresh capabilities

### 📊 Data Models
- **LogEntry**: Structured log data with metadata
- **Incident**: Incident tracking with timeline and resolution status  
- **AgentMessage**: Inter-agent communication protocol

### 🔧 Testing & Utilities
- **Comprehensive Test Suite**: Validates all agent functionality
- **Performance Testing**: Measures log processing capabilities
- **Sample Data Generation**: Creates realistic operational and incident scenarios

## API Endpoints

The web interface provides a REST API for programmatic access:

### System Health
```bash
# Get overall system health
curl http://localhost:8000/api/system/health

# Get system metrics
curl http://localhost:8000/api/metrics

# Get agent status
curl http://localhost:8000/api/agents/status
```

### Incident Management
```bash
# List all incidents
curl http://localhost:8000/api/incidents

# Get specific incident
curl http://localhost:8000/api/incidents/{incident_id}

# Get remediation plan
curl http://localhost:8000/api/incidents/{incident_id}/remediation

# Resolve incident
curl -X POST http://localhost:8000/api/incidents/{incident_id}/resolve
```

### Log Processing
```bash
# Upload log file for processing
curl -X POST http://localhost:8000/api/logs/upload \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/logfile.log"}'

# Simulate test incident
curl -X POST http://localhost:8000/api/simulate/incident
```

## Example Workflows

### 1. Basic Incident Response
```python
import requests

# Check system health
health = requests.get("http://localhost:8000/api/system/health").json()
print(f"System status: {health['overall_status']}")

# Get active incidents
incidents = requests.get("http://localhost:8000/api/incidents?status=open").json()
for incident in incidents:
    print(f"Incident: {incident['title']} ({incident['severity']})")
    
    # Get remediation plan
    plan = requests.get(f"http://localhost:8000/api/incidents/{incident['id']}/remediation").json()
    print(f"Remediation steps: {len(plan['detailed_steps'])}")
```

### 2. Log Processing Pipeline
```python
# Process a log file
response = requests.post("http://localhost:8000/api/logs/upload", json={
    "file_path": "/path/to/application.log",
    "force_reprocess": False
})

# Check for new incidents after processing
incidents = requests.get("http://localhost:8000/api/incidents").json()
print(f"Total incidents: {len(incidents)}")
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python scripts/test_agents.py

# Run with performance testing
python scripts/test_agents.py --performance

# Run with debug logging
python scripts/test_agents.py --log-level DEBUG
```

The test suite validates:
- ✅ Log ingestion and anomaly detection
- ✅ Incident detection and root cause analysis  
- ✅ Remediation plan generation
- ✅ Inter-agent message passing
- ✅ End-to-end incident response workflow
- ✅ Performance under load

## Extending the MVP

The MVP is designed to be easily extensible:

### Adding New Agents
1. Inherit from `BaseAgent` in `agents/base_agent.py`
2. Implement `process_message()` and `run()` methods
3. Register with the message bus and agent registry

### Adding New Incident Types
1. Add patterns to `analyzer.py` incident detection
2. Create remediation templates in `remediation.py`  
3. Update the web interface for new incident attributes

### Integrating External Systems
1. Create new message types in `models/__init__.py`
2. Add external API clients as needed
3. Implement webhooks or polling in agent run loops

## Limitations & Future Enhancements

This MVP demonstrates core concepts but has several limitations:

### Current Limitations
- 🔶 **No Persistence**: Data stored in memory only
- 🔶 **Limited Integrations**: No external monitoring/alerting systems  
- 🔶 **Single Instance**: No clustering or high availability
- 🔶 **Mock Data**: Simulated logs, no real system integration

### Planned Enhancements (Full Implementation)
- 🎯 **Advanced AI**: Enhanced Bedrock model integration with fine-tuning
- 🎯 **Knowledge Learning**: Continuous improvement from incident history
- 🎯 **External Integrations**: PagerDuty, Slack, monitoring tools
- 🎯 **Advanced Analytics**: Pattern recognition and predictive analysis
- 🎯 **Automated Execution**: Safe automation with approval workflows
- 🎯 **Multi-tenant**: Support for multiple teams and environments

## AI Integration - Amazon Bedrock

This MVP integrates with **Amazon Bedrock** for advanced AI capabilities:

### Supported Models
- **Claude 3 Haiku**: Fast, cost-effective analysis (default)
- **Claude 3 Sonnet**: Balanced performance for complex reasoning
- **Claude 3 Opus**: Advanced reasoning for critical incidents

### AI-Powered Features
- 🧠 **Smart Log Analysis**: Natural language understanding of log patterns
- 🔍 **Root Cause Analysis**: Multi-step reasoning with confidence scoring
- 📋 **Remediation Planning**: Context-aware runbook generation
- 📊 **Incident Summarization**: Automated incident report generation

### Setup Instructions

1. **Configure AWS Credentials**:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=us-east-1
   ```

2. **Enable Bedrock Models**:
   - Log into AWS Console → Amazon Bedrock
   - Request access to Anthropic Claude models
   - Wait for approval (usually instant for Claude Haiku)

3. **Test Connection**:
   ```bash
   python -c "from bedrock_client import test_bedrock_connection; import asyncio; asyncio.run(test_bedrock_connection())"
   ```

**Fallback Behavior**: If Bedrock is not available, the system automatically falls back to pattern-based analysis with mock AI responses, ensuring the MVP works without AWS credentials.
