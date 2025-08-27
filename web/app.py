"""
FastAPI Web Interface for NEXUS MVP
Provides REST API and simple web dashboard for incident management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from models import Incident, LogEntry, AgentMessage, MessageType
from agents.log_ingester import LogIngesterAgent
from agents.analyzer import AnalyzerAgent  
from agents.remediation import RemediationAgent

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Pydantic models for API
class IncidentResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    affected_services: List[str]
    first_seen: datetime
    last_seen: datetime
    resolved_at: Optional[datetime] = None

class RemediationPlanResponse(BaseModel):
    incident_id: str
    incident_type: str
    priority: str
    estimated_resolution_time: str
    immediate_actions: List[str]
    detailed_steps: List[Dict]
    generated_at: str

class SystemHealthResponse(BaseModel):
    overall_status: str
    active_incidents: int
    critical_incidents: int
    agents_online: int
    last_updated: datetime

class LogUploadRequest(BaseModel):
    file_path: str
    force_reprocess: bool = False

class RunbookExecuteRequest(BaseModel):
    step_id: str


class NexusWebApp:
    """Main web application for NEXUS"""
    
    def __init__(self):
        self.app = FastAPI(
            title="NEXUS - Incident Response Platform",
            description="AI-powered incident response and MTTR reduction platform",
            version="1.0.0"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize agents
        self.log_ingester = LogIngesterAgent()
        self.analyzer = AnalyzerAgent()
        self.remediation = RemediationAgent()
        
        # In-memory storage for demo (replace with proper database)
        self.incidents: Dict[str, Incident] = {}
        self.remediation_plans: Dict[str, Dict] = {}
        self.runbooks: Dict[str, Dict] = {}
        self.agent_activities: Dict[str, List[Dict]] = {
            'log_ingester': [],
            'analyzer': [],
            'remediation': []
        }
        self.system_metrics = {
            'incidents_total': 0,
            'incidents_resolved': 0,
            'avg_resolution_time': 0,
            'agents_status': {}
        }
        
        self._setup_routes()
        self._setup_static_files()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Serve main dashboard"""
            return self._get_dashboard_html()
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        
        @self.app.get("/api/system/health", response_model=SystemHealthResponse)
        async def get_system_health():
            """Get overall system health status"""
            active_incidents = len([i for i in self.incidents.values() if i.status == 'open'])
            critical_incidents = len([i for i in self.incidents.values() 
                                   if i.status == 'open' and i.severity == 'critical'])
            
            return SystemHealthResponse(
                overall_status="healthy" if critical_incidents == 0 else "degraded",
                active_incidents=active_incidents,
                critical_incidents=critical_incidents,
                agents_online=3,  # log_ingester, analyzer, remediation
                last_updated=datetime.utcnow()
            )
        
        @self.app.get("/api/incidents", response_model=List[IncidentResponse])
        async def get_incidents(
            status: Optional[str] = None,
            severity: Optional[str] = None,
            limit: int = 50
        ):
            """Get list of incidents with optional filtering"""
            incidents = list(self.incidents.values())
            
            # Apply filters
            if status:
                incidents = [i for i in incidents if i.status == status]
            if severity:
                incidents = [i for i in incidents if i.severity == severity]
            
            # Sort by updated_at descending and limit
            incidents.sort(key=lambda x: x.updated_at, reverse=True)
            incidents = incidents[:limit]
            
            # Convert to response format with proper attribute mapping
            response_incidents = []
            for incident in incidents:
                response_data = incident.__dict__.copy()
                response_data['first_seen'] = incident.created_at
                response_data['last_seen'] = incident.updated_at
                response_incidents.append(IncidentResponse(**response_data))
            
            return response_incidents
        
        @self.app.get("/api/incidents/{incident_id}", response_model=IncidentResponse)
        async def get_incident(incident_id: str):
            """Get specific incident by ID"""
            if incident_id not in self.incidents:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            incident = self.incidents[incident_id]
            return IncidentResponse(**incident.__dict__)
        
        @self.app.post("/api/incidents/{incident_id}/resolve")
        async def resolve_incident(incident_id: str):
            """Mark incident as resolved"""
            if incident_id not in self.incidents:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            incident = self.incidents[incident_id]
            incident.status = "resolved"
            incident.resolved_at = datetime.utcnow()
            
            self.system_metrics['incidents_resolved'] += 1
            
            return {"status": "success", "message": f"Incident {incident_id} resolved"}
        
        @self.app.get("/api/incidents/{incident_id}/remediation", response_model=RemediationPlanResponse)
        async def get_remediation_plan(incident_id: str):
            """Get remediation plan for incident"""
            if incident_id not in self.incidents:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            # Check if remediation plan already exists
            if incident_id in self.remediation_plans:
                plan = self.remediation_plans[incident_id]
                return RemediationPlanResponse(**plan)
            
            # Generate new remediation plan
            incident = self.incidents[incident_id]
            plan = await self.remediation.generate_remediation_plan(incident)
            self.remediation_plans[incident_id] = plan
            
            return RemediationPlanResponse(**plan)
        
        @self.app.post("/api/incidents/{incident_id}/remediation/execute")
        async def execute_remediation(incident_id: str, step_number: int):
            """Execute a specific remediation step"""
            if incident_id not in self.remediation_plans:
                raise HTTPException(status_code=404, detail="Remediation plan not found")
            
            plan = self.remediation_plans[incident_id]
            steps = plan.get('detailed_steps', [])
            
            if step_number < 1 or step_number > len(steps):
                raise HTTPException(status_code=400, detail="Invalid step number")
            
            step = steps[step_number - 1]
            
            # For demo, just return the commands to execute
            return {
                "status": "success",
                "step": step,
                "commands": step.get('commands', []),
                "message": f"Step {step_number} ready for execution"
            }
        
        @self.app.post("/api/logs/upload")
        async def upload_logs(background_tasks: BackgroundTasks, file: UploadFile = File(...), force_reprocess: bool = False):
            """Upload and process log files"""
            try:
                # Validate file type
                allowed_extensions = {'.jsonl', '.log', '.txt'}
                file_extension = Path(file.filename).suffix.lower()
                
                if file_extension not in allowed_extensions:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
                    )
                
                # Create uploads directory if it doesn't exist
                uploads_dir = Path("data/uploads")
                uploads_dir.mkdir(parents=True, exist_ok=True)
                
                # Save uploaded file with timestamp to avoid conflicts
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{timestamp}_{file.filename}"
                file_path = uploads_dir / safe_filename
                
                # Save the uploaded file
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # Process logs in background
                background_tasks.add_task(
                    self._process_uploaded_logs, 
                    str(file_path), 
                    force_reprocess
                )
                
                return {
                    "status": "accepted",
                    "message": f"Log file '{file.filename}' uploaded and queued for processing",
                    "file_path": str(file_path),
                    "file_size": len(content)
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        
        @self.app.get("/api/agents/status")
        async def get_agent_status():
            """Get status of all agents"""
            return {
                "log_ingester": {
                    "status": "running",
                    "last_heartbeat": datetime.utcnow(),
                    "processed_files": getattr(self.log_ingester, 'processed_files', 0),
                    "current_activity": self._get_agent_current_activity('log_ingester'),
                    "recent_actions": self._get_recent_agent_actions('log_ingester')
                },
                "analyzer": {
                    "status": "running", 
                    "last_heartbeat": datetime.utcnow(),
                    "incidents_detected": len(self.incidents),
                    "current_activity": self._get_agent_current_activity('analyzer'),
                    "recent_actions": self._get_recent_agent_actions('analyzer')
                },
                "remediation": {
                    "status": "running",
                    "last_heartbeat": datetime.utcnow(),
                    "plans_generated": len(self.remediation_plans),
                    "current_activity": self._get_agent_current_activity('remediation'),
                    "recent_actions": self._get_recent_agent_actions('remediation')
                }
            }
        
        @self.app.get("/api/incidents/{incident_id}/runbook")
        async def generate_runbook(incident_id: str):
            """Generate a detailed runbook for incident resolution"""
            if incident_id not in self.incidents:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            # Check if runbook already exists
            if incident_id in self.runbooks:
                return self.runbooks[incident_id]
            
            # Generate new runbook
            incident = self.incidents[incident_id]
            runbook = await self._generate_incident_runbook(incident)
            self.runbooks[incident_id] = runbook
            
            return runbook
        
        @self.app.post("/api/incidents/{incident_id}/runbook/execute")
        async def execute_runbook_step(incident_id: str, request: RunbookExecuteRequest):
            """Execute a specific runbook step"""
            if incident_id not in self.runbooks:
                raise HTTPException(status_code=404, detail="Runbook not found")
            
            step_id = request.step_id
            runbook = self.runbooks[incident_id]
            
            # Find the step
            step = None
            for section in runbook.get('sections', []):
                for s in section.get('steps', []):
                    if s.get('id') == step_id:
                        step = s
                        break
                if step:
                    break
            
            if not step:
                raise HTTPException(status_code=404, detail="Step not found")
            
            # Mark step as executed
            step['executed'] = True
            step['executed_at'] = datetime.utcnow().isoformat()
            
            # Log agent activity
            self._log_agent_activity('remediation', 'step_executed', {
                'incident_id': incident_id,
                'step_id': step_id,
                'step_title': step.get('title'),
                'execution_time': datetime.utcnow().isoformat()
            })
            
            return {
                "status": "success",
                "step": step,
                "message": f"Step '{step.get('title')}' marked as executed"
            }
        
        @self.app.get("/api/agents/activities")
        async def get_agent_activities():
            """Get detailed agent activities"""
            return {
                "activities": self.agent_activities,
                "summary": {
                    "total_actions": sum(len(actions) for actions in self.agent_activities.values()),
                    "last_updated": datetime.utcnow()
                }
            }
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get system metrics and statistics"""
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            
            recent_incidents = [
                i for i in self.incidents.values() 
                if i.created_at >= last_24h
            ]
            
            resolved_incidents = [
                i for i in self.incidents.values()
                if i.status == 'resolved' and i.resolved_at
            ]
            
            # Calculate average resolution time
            if resolved_incidents:
                resolution_times = [
                    (i.resolved_at - i.created_at).total_seconds() / 60  # minutes
                    for i in resolved_incidents
                    if i.resolved_at
                ]
                avg_resolution_time = sum(resolution_times) / len(resolution_times)
            else:
                avg_resolution_time = 0
            
            return {
                "total_incidents": len(self.incidents),
                "active_incidents": len([i for i in self.incidents.values() if i.status == 'open']),
                "resolved_incidents": len(resolved_incidents),
                "incidents_last_24h": len(recent_incidents),
                "avg_resolution_time_minutes": round(avg_resolution_time, 2),
                "severity_breakdown": {
                    "critical": len([i for i in self.incidents.values() if i.severity == 'critical']),
                    "high": len([i for i in self.incidents.values() if i.severity == 'high']),
                    "medium": len([i for i in self.incidents.values() if i.severity == 'medium']),
                    "low": len([i for i in self.incidents.values() if i.severity == 'low'])
                },
                "last_updated": now
            }
        
        @self.app.post("/api/simulate/incident")
        async def simulate_incident(background_tasks: BackgroundTasks):
            """Simulate an incident for testing"""
            background_tasks.add_task(self._simulate_test_incident)
            return {"status": "success", "message": "Test incident simulation started"}
        
        @self.app.post("/api/incidents/{incident_id}/resolve")
        async def resolve_incident(incident_id: str):
            """Manually resolve an incident"""
            if incident_id not in self.incidents:
                raise HTTPException(status_code=404, detail="Incident not found")
            
            incident = self.incidents[incident_id]
            if incident.status == 'resolved':
                return {"status": "error", "message": "Incident already resolved"}
            
            incident.status = 'resolved'
            incident.resolved_at = datetime.utcnow()
            incident.updated_at = datetime.utcnow()
            
            return {
                "status": "success", 
                "message": f"Incident {incident_id} resolved successfully",
                "incident": {
                    "id": incident.id,
                    "title": incident.title,
                    "status": incident.status,
                    "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None
                }
            }
    
    def _setup_static_files(self):
        """Setup static file serving"""
        # Create static directory if it doesn't exist
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    def _get_dashboard_html(self) -> str:
        """Generate HTML for the main dashboard"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS - Incident Response Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 1rem 2rem; }
        .header h1 { margin: 0; }
        .header .subtitle { opacity: 0.8; margin-top: 0.5rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .metric-card { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-card h3 { color: #2c3e50; margin-bottom: 0.5rem; }
        .metric-value { font-size: 2rem; font-weight: bold; }
        .metric-value.critical { color: #e74c3c; }
        .metric-value.warning { color: #f39c12; }
        .metric-value.success { color: #27ae60; }
        .section { background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem; }
        .section h2 { color: #2c3e50; margin-bottom: 1rem; }
        .incident-list { max-height: 400px; overflow-y: auto; }
        .incident-item { padding: 1rem; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; align-items: center; }
        .incident-item:last-child { border-bottom: none; }
        .incident-info h4 { margin: 0; color: #2c3e50; }
        .incident-info p { margin: 0.25rem 0; color: #7f8c8d; font-size: 0.9rem; }
        .severity-badge { padding: 0.25rem 0.5rem; border-radius: 4px; color: white; font-size: 0.8rem; font-weight: bold; }
        .severity-critical { background: #e74c3c; }
        .severity-high { background: #e67e22; }
        .severity-medium { background: #f39c12; }
        .severity-low { background: #3498db; }
        .btn { padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 0.25rem; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.8rem; }
        .refresh-btn { float: right; }
        .loading { text-align: center; padding: 2rem; color: #7f8c8d; }
        .agent-card { display: inline-block; margin: 0.5rem; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; min-width: 250px; vertical-align: top; }
        .agent-status { margin: 0.5rem 0; }
        .agent-activity { font-size: 0.9rem; color: #555; margin: 0.25rem 0; }
        .activity-log { max-height: 150px; overflow-y: auto; background: #f8f9fa; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; }
        .activity-item { font-size: 0.8rem; padding: 0.25rem 0; border-bottom: 1px solid #e9ecef; }
        .activity-item:last-child { border-bottom: none; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: white; margin: 5% auto; padding: 2rem; width: 90%; max-width: 800px; border-radius: 8px; max-height: 80vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .close { font-size: 2rem; cursor: pointer; }
        .runbook-section { margin: 1rem 0; border: 1px solid #ddd; border-radius: 8px; }
        .runbook-section-header { background: #f8f9fa; padding: 1rem; border-bottom: 1px solid #ddd; cursor: pointer; }
        .runbook-section-content { padding: 1rem; display: none; }
        .runbook-step { margin: 0.5rem 0; padding: 1rem; border-left: 4px solid #3498db; background: #f8f9fa; }
        .runbook-step.completed { border-left-color: #27ae60; background: #d5f4e6; }
        .runbook-step-commands { background: #2c3e50; color: white; padding: 0.5rem; border-radius: 4px; font-family: monospace; margin: 0.5rem 0; font-size: 0.9rem; }
        .step-execute-btn { margin-top: 0.5rem; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 NEXUS</h1>
        <div class="subtitle">AI-Powered Incident Response Platform</div>
    </div>
    
    <div class="container">
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>System Health</h3>
                <div class="metric-value success" id="system-health">Healthy</div>
            </div>
            <div class="metric-card">
                <h3>Active Incidents</h3>
                <div class="metric-value" id="active-incidents">-</div>
            </div>
            <div class="metric-card">
                <h3>Critical Incidents</h3>
                <div class="metric-value critical" id="critical-incidents">-</div>
            </div>
            <div class="metric-card">
                <h3>Avg Resolution Time</h3>
                <div class="metric-value" id="avg-resolution">-</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Log File Upload</h2>
            <div style="margin-bottom: 1rem;">
                <input type="file" id="logFileInput" accept=".jsonl,.log,.txt" style="margin-right: 1rem;">
                <button class="btn btn-primary" onclick="uploadLogFile()">Upload & Analyze</button>
                <button class="btn btn-warning" onclick="uploadLogFile(true)" style="margin-left: 0.5rem;">Force Reprocess</button>
            </div>
            <div id="uploadStatus" style="margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; display: none;"></div>
            <div style="margin-top: 1rem; font-size: 0.9rem; color: #666;">
                <strong>Supported formats:</strong> .jsonl (JSON Lines), .log, .txt<br>
                <strong>Sample files:</strong> Check the <code>data/logs/</code> directory for pre-generated sample log files.
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Incidents 
                <button class="btn btn-primary btn-sm refresh-btn" onclick="refreshDashboard()">Refresh</button>
                <button class="btn btn-success btn-sm refresh-btn" onclick="simulateIncident()" style="margin-right: 0.5rem;">Simulate Incident</button>
            </h2>
            <div class="incident-list" id="incident-list">
                <div class="loading">Loading incidents...</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Agent Status</h2>
            <div id="agent-status">
                <div class="loading">Loading agent status...</div>
            </div>
        </div>
    </div>

    <!-- Runbook Modal -->
    <div id="runbookModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="runbook-title">Incident Runbook</h2>
                <span class="close" onclick="closeRunbook()">&times;</span>
            </div>
            <div id="runbook-content">
                <div class="loading">Loading runbook...</div>
            </div>
        </div>
    </div>

    <script>
        async function fetchData(url) {
            try {
                const response = await fetch(url);
                return await response.json();
            } catch (error) {
                console.error('Error fetching data:', error);
                return null;
            }
        }
        
        async function updateMetrics() {
            const health = await fetchData('/api/system/health');
            const metrics = await fetchData('/api/metrics');
            
            if (health) {
                document.getElementById('system-health').textContent = health.overall_status;
                document.getElementById('system-health').className = 'metric-value ' + 
                    (health.overall_status === 'healthy' ? 'success' : 'warning');
                document.getElementById('active-incidents').textContent = health.active_incidents;
                document.getElementById('critical-incidents').textContent = health.critical_incidents;
            }
            
            if (metrics) {
                document.getElementById('avg-resolution').textContent = 
                    metrics.avg_resolution_time_minutes + ' min';
            }
        }
        
        async function updateIncidents() {
            const incidents = await fetchData('/api/incidents');
            const container = document.getElementById('incident-list');
            
            if (!incidents || incidents.length === 0) {
                container.innerHTML = '<div class="loading">No incidents found</div>';
                return;
            }
            
            container.innerHTML = incidents.map(incident => `
                <div class="incident-item">
                    <div class="incident-info">
                        <h4>${incident.title}</h4>
                        <p>${incident.description}</p>
                        <p>Affected: ${incident.affected_services.join(', ')}</p>
                        <p>Created: ${new Date(incident.first_seen).toLocaleString()}</p>
                    </div>
                    <div>
                        <span class="severity-badge severity-${incident.severity}">${incident.severity}</span>
                        <br><br>
                        <a href="#" class="btn btn-primary btn-sm" onclick="viewIncident('${incident.id}')">View</a>
                        <a href="#" class="btn btn-warning btn-sm" onclick="viewRunbook('${incident.id}')">Runbook</a>
                        ${incident.status === 'open' ? `<a href="#" class="btn btn-success btn-sm" onclick="resolveIncident('${incident.id}')">Resolve</a>` : ''}
                    </div>
                </div>
            `).join('');
        }
        
        async function updateAgentStatus() {
            const status = await fetchData('/api/agents/status');
            const container = document.getElementById('agent-status');
            
            if (!status) {
                container.innerHTML = '<div class="loading">Error loading agent status</div>';
                return;
            }
            
            container.innerHTML = Object.entries(status).map(([agent, info]) => `
                <div class="agent-card">
                    <strong>${agent.replace('_', ' ').toUpperCase()}</strong><br>
                    <div class="agent-status">
                        <span style="color: ${info.status === 'running' ? '#27ae60' : '#e74c3c'};">
                            ● ${info.status}
                        </span>
                    </div>
                    <div class="agent-activity">
                        <strong>Current:</strong> ${info.current_activity || 'Idle'}
                    </div>
                    <div class="activity-log">
                        <strong>Recent Actions:</strong>
                        ${(info.recent_actions || []).map(action => `
                            <div class="activity-item">
                                <small>${new Date(action.timestamp).toLocaleTimeString()}</small><br>
                                ${action.action}: ${action.details?.action || 'No details'}
                            </div>
                        `).join('') || '<div class="activity-item">No recent activity</div>'}
                    </div>
                </div>
            `).join('');
        }
        
        async function refreshDashboard() {
            await Promise.all([
                updateMetrics(),
                updateIncidents(),
                updateAgentStatus()
            ]);
        }
        
        async function uploadLogFile(forceReprocess = false) {
            const fileInput = document.getElementById('logFileInput');
            const statusDiv = document.getElementById('uploadStatus');
            
            if (!fileInput.files.length) {
                showUploadStatus('Please select a file to upload', 'error');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                showUploadStatus('Uploading file...', 'info');
                
                const response = await fetch('/api/logs/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showUploadStatus(`✅ ${result.message}`, 'success');
                    // Refresh dashboard after a short delay to show new incidents
                    setTimeout(() => {
                        refreshDashboard();
                        showUploadStatus('File processed successfully! Check for new incidents below.', 'success');
                    }, 3000);
                } else {
                    showUploadStatus(`❌ Upload failed: ${result.detail || 'Unknown error'}`, 'error');
                }
            } catch (error) {
                showUploadStatus(`❌ Upload error: ${error.message}`, 'error');
            }
        }
        
        function showUploadStatus(message, type) {
            const statusDiv = document.getElementById('uploadStatus');
            statusDiv.style.display = 'block';
            statusDiv.textContent = message;
            
            // Reset classes
            statusDiv.className = '';
            
            // Apply styling based on type
            if (type === 'success') {
                statusDiv.style.background = '#d5f4e6';
                statusDiv.style.color = '#155724';
                statusDiv.style.border = '1px solid #c3e6cb';
            } else if (type === 'error') {
                statusDiv.style.background = '#f8d7da';
                statusDiv.style.color = '#721c24';
                statusDiv.style.border = '1px solid #f5c6cb';
            } else if (type === 'info') {
                statusDiv.style.background = '#d1ecf1';
                statusDiv.style.color = '#0c5460';
                statusDiv.style.border = '1px solid #bee5eb';
            }
        }
        
        async function simulateIncident() {
            try {
                const response = await fetch('/api/simulate/incident', { method: 'POST' });
                const result = await response.json();
                alert(result.message);
                setTimeout(refreshDashboard, 2000); // Refresh after 2 seconds
            } catch (error) {
                alert('Error simulating incident: ' + error.message);
            }
        }
        
        function viewIncident(incidentId) {
            alert(`Viewing incident ${incidentId}\\n\\nIn a full implementation, this would open a detailed incident view with:\\n- Timeline\\n- Remediation plan\\n- Execution status\\n- Related logs`);
        }
        
        async function viewRunbook(incidentId) {
            const modal = document.getElementById('runbookModal');
            const content = document.getElementById('runbook-content');
            const title = document.getElementById('runbook-title');
            
            // Show modal
            modal.style.display = 'block';
            content.innerHTML = '<div class="loading">Loading runbook...</div>';
            
            try {
                const runbook = await fetchData(`/api/incidents/${incidentId}/runbook`);
                
                if (!runbook) {
                    content.innerHTML = '<div class="loading">Error loading runbook</div>';
                    return;
                }
                
                title.textContent = runbook.title || `Runbook for Incident ${incidentId}`;
                
                content.innerHTML = `
                    <div style="margin-bottom: 1rem;">
                        <strong>Severity:</strong> <span class="severity-badge severity-${runbook.severity || 'medium'}">${runbook.severity || 'medium'}</span>
                        <strong style="margin-left: 1rem;">Estimated Duration:</strong> ${runbook.estimated_duration || 'Unknown'}
                    </div>
                    
                    ${(runbook.sections || []).map((section, index) => `
                        <div class="runbook-section">
                            <div class="runbook-section-header" onclick="toggleSection(${index})">
                                <h3>${section.title}</h3>
                                <small>Priority: ${section.priority}</small>
                            </div>
                            <div class="runbook-section-content" id="section-${index}">
                                ${(section.steps || []).map(step => `
                                    <div class="runbook-step ${step.executed ? 'completed' : ''}">
                                        <h4>${step.title}</h4>
                                        <p>${step.description}</p>
                                        
                                        ${step.commands && step.commands.length > 0 ? `
                                            <div class="runbook-step-commands">
                                                ${step.commands.map(cmd => `<div>$ ${cmd}</div>`).join('')}
                                            </div>
                                        ` : ''}
                                        
                                        <div>
                                            <small><strong>Expected:</strong> ${step.expected_outcome || 'No outcome specified'}</small><br>
                                            <small><strong>Time:</strong> ${step.estimated_time || 'Unknown'}</small>
                                        </div>
                                        
                                        ${!step.executed ? `
                                            <button class="btn btn-success btn-sm step-execute-btn" onclick="executeStep('${incidentId}', '${step.id}')">
                                                Mark as Executed
                                            </button>
                                        ` : `
                                            <div style="color: #27ae60; margin-top: 0.5rem;">
                                                ✓ Executed at ${step.executed_at ? new Date(step.executed_at).toLocaleString() : 'Unknown time'}
                                            </div>
                                        `}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                `;
                
            } catch (error) {
                content.innerHTML = `<div class="loading">Error: ${error.message}</div>`;
            }
        }
        
        function toggleSection(index) {
            const section = document.getElementById(`section-${index}`);
            section.style.display = section.style.display === 'block' ? 'none' : 'block';
        }
        
        async function executeStep(incidentId, stepId) {
            try {
                const response = await fetch(`/api/incidents/${incidentId}/runbook/execute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ step_id: stepId })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Step executed successfully: ${result.message}`);
                    // Refresh the runbook
                    viewRunbook(incidentId);
                } else {
                    alert(`Error executing step: ${result.detail || 'Unknown error'}`);
                }
            } catch (error) {
                alert(`Error executing step: ${error.message}`);
            }
        }
        
        function closeRunbook() {
            document.getElementById('runbookModal').style.display = 'none';
        }
        
        async function resolveIncident(incidentId) {
            try {
                const response = await fetch(`/api/incidents/${incidentId}/resolve`, { method: 'POST' });
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Incident resolved: ${result.message}`);
                    refreshDashboard();
                } else {
                    alert(`Error resolving incident: ${result.detail || 'Unknown error'}`);
                }
            } catch (error) {
                alert(`Error resolving incident: ${error.message}`);
            }
        }
        
        // Initial load and periodic refresh
        refreshDashboard();
        setInterval(refreshDashboard, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
        """
    
    async def _process_uploaded_logs(self, file_path: str, force_reprocess: bool):
        """Process uploaded log files in background"""
        try:
            logger.info(f"Background task: Processing uploaded log file: {file_path}")
            logger.info(f"Background task: Current incidents count: {len(self.incidents)}")
            
            # Use log ingester to process the file
            result = await self.log_ingester.process_log_file(file_path)
            logger.info(f"Background task: Log ingester result - {len(result.get('log_entries', []))} entries, {len(result.get('anomalies', []))} anomalies")
            
            if result and result.get('anomalies'):
                logger.info(f"Background task: Found anomalies, analyzing with analyzer")
                
                # Analyze for incidents
                analyze_message = AgentMessage(
                    sender_id="web-interface",
                    recipient_id="analyzer-agent",
                    message_type=MessageType.LOG_ANALYSIS,
                    data=result,
                    timestamp=datetime.utcnow()
                )
                
                analysis_result = await self.analyzer.process_message(analyze_message)
                logger.info(f"Background task: Analyzer result: {analysis_result is not None}")
                
                if analysis_result and analysis_result.data.get('incidents'):
                    incidents_data = analysis_result.data['incidents']
                    logger.info(f"Background task: Creating {len(incidents_data)} incidents")
                    
                    # Create incidents from the analyzer results
                    for incident_data in incidents_data:
                        incident = Incident(**incident_data)
                        self.incidents[incident.id] = incident
                        self.system_metrics['incidents_total'] += 1
                        
                        logger.info(f"Background task: Created incident {incident.id} - {incident.title}")
                        
                        # Log activity
                        self._log_agent_activity('analyzer', 'incident_detection', {
                            'incident_id': incident.id,
                            'incident_title': incident.title,
                            'severity': incident.severity,
                            'affected_services': incident.affected_services,
                            'source': 'uploaded_logs'
                        })
                    
                    logger.info(f"Background task: Total incidents now: {len(self.incidents)}")
                else:
                    logger.info("Background task: No incidents detected from uploaded logs")
            else:
                logger.info("Background task: No anomalies found in uploaded logs")
            
        except Exception as e:
            logger.error(f"Background task: Error processing uploaded logs: {e}")
            import traceback
            logger.error(f"Background task: Traceback: {traceback.format_exc()}")
    
    async def _simulate_test_incident(self):
        """Simulate a test incident for demonstration"""
        try:
            import random
            
            # Log activity
            self._log_agent_activity('log_ingester', 'log_processing', {
                'action': 'Processing simulated log anomaly',
                'severity': 'medium'
            })
            
            # Random severity with weighted distribution
            severities = ["critical", "high", "medium", "low"]
            severity_weights = [0.15, 0.35, 0.35, 0.15]  # 15% critical, 35% high, 35% medium, 15% low
            severity = random.choices(severities, weights=severity_weights)[0]
            
            # Random incident types
            incident_types = [
                ("High CPU Usage", "CPU usage exceeded 95% on {service}", ["web-server-01", "api-server-02", "worker-01"]),
                ("Database Connection Timeout", "Database connection pool exhausted on {service}", ["db-primary", "db-replica"]),
                ("Memory Leak Detected", "Memory usage exceeding 90% on {service}", ["api-server-01", "web-server-02"]),
                ("Service Unavailable", "Service {service} is not responding to health checks", ["payment-service", "auth-service", "notification-service"]),
                ("Disk Space Critical", "Disk usage exceeded 95% on {service}", ["log-server", "backup-server"]),
                ("Network Latency High", "Network latency to {service} exceeding 5000ms", ["external-api", "cdn-endpoint"])
            ]
            
            incident_type = random.choice(incident_types)
            service = random.choice(incident_type[2]);
            
            # Log analyzer activity
            self._log_agent_activity('analyzer', 'incident_analysis', {
                'action': f'Analyzing {incident_type[0]} on {service}',
                'severity': severity,
                'affected_service': service
            })
            
            # Create a test incident
            incident = Incident(
                id=f"sim-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}",
                title=f"Simulated {incident_type[0]}",
                description=f"Simulated incident: {incident_type[1].format(service=service)}",
                severity=severity,
                status="open",
                affected_services=[service],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add to incidents
            self.incidents[incident.id] = incident
            self.system_metrics['incidents_total'] += 1
            
            # Log remediation activity
            self._log_agent_activity('remediation', 'plan_generation', {
                'action': f'Generating remediation plan for incident {incident.id}',
                'incident_type': incident_type[0],
                'severity': severity
            })
            
            # Generate remediation plan
            plan = await self.remediation.generate_remediation_plan(incident)
            self.remediation_plans[incident.id] = plan
            
            # Randomly resolve some older incidents to show resolution times
            await self._randomly_resolve_incidents()
            
            logger.info(f"Simulated incident created: {incident.id} (severity: {severity})")
            
        except Exception as e:
            logger.error(f"Error simulating incident: {e}")
    
    async def _randomly_resolve_incidents(self):
        """Randomly resolve some older incidents to demonstrate resolution times"""
        import random
        
        # Find open incidents older than 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        old_incidents = [
            inc for inc in self.incidents.values() 
            if inc.status == "open" and inc.created_at < cutoff_time
        ]
        
        # Resolve 30% of old incidents randomly
        incidents_to_resolve = random.sample(
            old_incidents, 
            min(len(old_incidents), max(1, int(len(old_incidents) * 0.3)))
        )
        
        for incident in incidents_to_resolve:
            # Calculate resolution time (5-60 minutes randomly)
            resolution_time = random.randint(5, 60)
            resolved_at = incident.created_at + timedelta(minutes=resolution_time)
            
            incident.status = "resolved"
            incident.resolved_at = resolved_at
            incident.updated_at = resolved_at
            
            logger.info(f"Auto-resolved incident {incident.id} after {resolution_time} minutes")
    
    def _log_agent_activity(self, agent_name: str, action: str, details: Dict):
        """Log agent activity for tracking"""
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details
        }
        
        # Keep only last 50 activities per agent
        if len(self.agent_activities[agent_name]) >= 50:
            self.agent_activities[agent_name] = self.agent_activities[agent_name][-49:]
        
        self.agent_activities[agent_name].append(activity)
    
    def _get_agent_current_activity(self, agent_name: str) -> str:
        """Get current activity description for agent"""
        if not self.agent_activities[agent_name]:
            return "Idle - waiting for tasks"
        
        last_activity = self.agent_activities[agent_name][-1]
        action = last_activity.get('action', 'unknown')
        
        activity_descriptions = {
            'log_processing': 'Processing log files for anomalies',
            'incident_analysis': 'Analyzing potential incidents',
            'plan_generation': 'Generating remediation plans',
            'step_executed': 'Executing remediation steps',
            'monitoring': 'Monitoring system health',
            'idle': 'Idle - waiting for tasks'
        }
        
        return activity_descriptions.get(action, f"Performing {action}")
    
    def _get_recent_agent_actions(self, agent_name: str, limit: int = 5) -> List[Dict]:
        """Get recent actions for an agent"""
        return self.agent_activities[agent_name][-limit:] if self.agent_activities[agent_name] else []
    
    async def _generate_incident_runbook(self, incident: Incident) -> Dict:
        """Generate a comprehensive runbook for incident resolution"""
        
        # Use Bedrock to generate intelligent runbook content
        try:
            from bedrock_client import BedrockClient
            bedrock = BedrockClient()
            
            prompt = f"""
Generate a detailed incident resolution runbook for the following incident:

Title: {incident.title}
Description: {incident.description}
Severity: {incident.severity}
Affected Services: {', '.join(incident.affected_services)}

Please provide a comprehensive runbook with:
1. Immediate Response Actions (first 5 minutes)
2. Investigation Steps
3. Resolution Procedures
4. Verification Steps
5. Post-Incident Actions

Format as JSON with sections and detailed steps including commands, checks, and expected outcomes.
"""
            
            response = await bedrock.generate_text(prompt)
            
            # Parse the response and structure it
            import json
            try:
                ai_runbook = json.loads(response)
            except:
                # Fallback to template if AI response isn't valid JSON
                ai_runbook = None
                
        except Exception as e:
            logger.warning(f"Failed to generate AI runbook: {e}")
            ai_runbook = None
        
        # Generate structured runbook (with AI enhancement or fallback template)
        runbook = {
            "incident_id": incident.id,
            "title": f"Runbook for {incident.title}",
            "severity": incident.severity,
            "estimated_duration": self._estimate_resolution_time(incident.severity),
            "generated_at": datetime.utcnow().isoformat(),
            "sections": []
        }
        
        if ai_runbook and isinstance(ai_runbook, dict):
            # Use AI-generated content
            runbook.update(ai_runbook)
        else:
            # Use template-based runbook
            runbook["sections"] = self._generate_template_runbook(incident)
        
        # Log the runbook generation
        self._log_agent_activity('remediation', 'runbook_generated', {
            'incident_id': incident.id,
            'sections_count': len(runbook.get('sections', [])),
            'generated_at': runbook['generated_at']
        })
        
        return runbook
    
    def _generate_template_runbook(self, incident: Incident) -> List[Dict]:
        """Generate template-based runbook sections"""
        sections = [
            {
                "title": "🚨 Immediate Response (0-5 minutes)",
                "priority": "critical",
                "steps": [
                    {
                        "id": "imm-1",
                        "title": "Acknowledge Incident",
                        "description": "Acknowledge the incident and notify stakeholders",
                        "commands": ["echo 'Incident acknowledged'"],
                        "expected_outcome": "Incident status updated to 'acknowledged'",
                        "estimated_time": "1 minute",
                        "executed": False
                    },
                    {
                        "id": "imm-2", 
                        "title": "Check Service Health",
                        "description": f"Verify health status of affected services: {', '.join(incident.affected_services)}",
                        "commands": [f"curl -f http://{service}/health" for service in incident.affected_services[:3]],
                        "expected_outcome": "Service health status determined",
                        "estimated_time": "2 minutes",
                        "executed": False
                    },
                    {
                        "id": "imm-3",
                        "title": "Enable Enhanced Monitoring",
                        "description": "Increase monitoring frequency and enable detailed logging",
                        "commands": [
                            "kubectl patch deployment monitoring-stack -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"monitor\",\"env\":[{\"name\":\"LOG_LEVEL\",\"value\":\"DEBUG\"}]}]}}}}'",
                            "aws cloudwatch put-metric-alarm --alarm-name incident-monitor --metric-name ErrorRate --threshold 0.1"
                        ],
                        "expected_outcome": "Enhanced monitoring active",
                        "estimated_time": "2 minutes",
                        "executed": False
                    }
                ]
            },
            {
                "title": "🔍 Investigation (5-15 minutes)",
                "priority": "high",
                "steps": [
                    {
                        "id": "inv-1",
                        "title": "Gather System Metrics",
                        "description": "Collect CPU, memory, disk, and network metrics",
                        "commands": [
                            "top -n 1 -b",
                            "df -h",
                            "free -m",
                            "netstat -i"
                        ],
                        "expected_outcome": "System resource utilization identified",
                        "estimated_time": "3 minutes",
                        "executed": False
                    },
                    {
                        "id": "inv-2",
                        "title": "Analyze Recent Logs",
                        "description": "Review logs from the last 30 minutes for error patterns",
                        "commands": [
                            "journalctl --since '30 minutes ago' --priority err",
                            "tail -1000 /var/log/application.log | grep ERROR",
                            "kubectl logs --tail=500 deployment/app --since=30m"
                        ],
                        "expected_outcome": "Error patterns and root cause indicators identified",
                        "estimated_time": "5 minutes",
                        "executed": False
                    },
                    {
                        "id": "inv-3",
                        "title": "Check Dependencies",
                        "description": "Verify external dependencies and downstream services",
                        "commands": [
                            "nslookup external-api.com",
                            "ping -c 5 database-server.internal",
                            "telnet redis-cluster 6379"
                        ],
                        "expected_outcome": "Dependency health status confirmed",
                        "estimated_time": "4 minutes",
                        "executed": False
                    }
                ]
            },
            {
                "title": "🔧 Resolution Procedures",
                "priority": "high", 
                "steps": self._get_resolution_steps(incident)
            },
            {
                "title": "✅ Verification",
                "priority": "medium",
                "steps": [
                    {
                        "id": "ver-1",
                        "title": "Service Health Check",
                        "description": "Verify all affected services are healthy",
                        "commands": [f"curl -f http://{service}/health && echo '{service} is healthy'" for service in incident.affected_services],
                        "expected_outcome": "All services responding normally",
                        "estimated_time": "3 minutes",
                        "executed": False
                    },
                    {
                        "id": "ver-2",
                        "title": "Performance Validation",
                        "description": "Confirm system performance is within normal parameters",
                        "commands": [
                            "curl -w '@curl-format.txt' -s -o /dev/null http://service/api/test",
                            "watch -n 5 'ps aux | grep service | head -5'"
                        ],
                        "expected_outcome": "Performance metrics within acceptable range",
                        "estimated_time": "5 minutes",
                        "executed": False
                    }
                ]
            },
            {
                "title": "📋 Post-Incident Actions",
                "priority": "low",
                "steps": [
                    {
                        "id": "post-1",
                        "title": "Update Documentation",
                        "description": "Document the incident and resolution steps",
                        "commands": ["echo 'Document incident resolution in wiki'"],
                        "expected_outcome": "Incident documented for future reference",
                        "estimated_time": "10 minutes",
                        "executed": False
                    },
                    {
                        "id": "post-2",
                        "title": "Schedule Post-Mortem",
                        "description": "Schedule post-mortem meeting with stakeholders",
                        "commands": ["calendar add 'Post-mortem for incident'"],
                        "expected_outcome": "Post-mortem meeting scheduled",
                        "estimated_time": "5 minutes",
                        "executed": False
                    }
                ]
            }
        ]
        
        return sections
    
    def _get_resolution_steps(self, incident: Incident) -> List[Dict]:
        """Generate resolution steps based on incident type"""
        if "CPU" in incident.title or "cpu" in incident.description.lower():
            return [
                {
                    "id": "res-1",
                    "title": "Identify High CPU Processes",
                    "description": "Find processes consuming high CPU",
                    "commands": ["ps aux --sort=-%cpu | head -10", "top -n 1 -b -o %CPU"],
                    "expected_outcome": "High CPU processes identified",
                    "estimated_time": "2 minutes",
                    "executed": False
                },
                {
                    "id": "res-2",
                    "title": "Scale Service",
                    "description": "Increase service replicas to handle load",
                    "commands": ["kubectl scale deployment/app --replicas=5"],
                    "expected_outcome": "Service scaled to handle increased load",
                    "estimated_time": "3 minutes",
                    "executed": False
                }
            ]
        elif "Memory" in incident.title or "memory" in incident.description.lower():
            return [
                {
                    "id": "res-1",
                    "title": "Identify Memory Leaks",
                    "description": "Find processes with high memory usage",
                    "commands": ["ps aux --sort=-%mem | head -10", "pmap -d $(pgrep service)"],
                    "expected_outcome": "Memory usage patterns identified",
                    "estimated_time": "3 minutes",
                    "executed": False
                },
                {
                    "id": "res-2",
                    "title": "Restart Service",
                    "description": "Restart service to clear memory",
                    "commands": ["kubectl rollout restart deployment/app"],
                    "expected_outcome": "Service restarted with cleared memory",
                    "estimated_time": "2 minutes",
                    "executed": False
                }
            ]
        else:
            return [
                {
                    "id": "res-1",
                    "title": "Restart Affected Service",
                    "description": f"Restart the affected service: {incident.affected_services[0] if incident.affected_services else 'main-service'}",
                    "commands": [f"systemctl restart {incident.affected_services[0] if incident.affected_services else 'main-service'}"],
                    "expected_outcome": "Service restarted successfully",
                    "estimated_time": "2 minutes",
                    "executed": False
                },
                {
                    "id": "res-2",
                    "title": "Clear Cache",
                    "description": "Clear application cache to ensure fresh state",
                    "commands": ["redis-cli FLUSHALL", "memcached-tool localhost:11211 flush_all"],
                    "expected_outcome": "Cache cleared",
                    "estimated_time": "1 minute",
                    "executed": False
                }
            ]
    
    def _estimate_resolution_time(self, severity: str) -> str:
        """Estimate resolution time based on severity"""
        time_estimates = {
            "critical": "15-30 minutes",
            "high": "30-60 minutes", 
            "medium": "1-4 hours",
            "low": "4-24 hours"
        }
        return time_estimates.get(severity, "1-2 hours")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    nexus_app = NexusWebApp()
    return nexus_app.app


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Run the web server"""
    import subprocess
    import sys
    import os
    
    # Get the current directory for the uvicorn command
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Use subprocess to avoid asyncio event loop issues
    cmd = [
        sys.executable, "-m", "uvicorn",
        "web.app:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        print(f"🌐 Starting web server at http://{host}:{port}")
        subprocess.run(cmd, cwd=current_dir, check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")


# Create the app instance at module level for uvicorn
app = create_app()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_server()
