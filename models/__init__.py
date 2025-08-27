"""
Data models for NEXUS MVP
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import uuid
import json

class MessageType(str, Enum):
    """Message types for agent communication"""
    LOG_ANALYSIS = "log_analysis"
    INCIDENT_DETECTED = "incident_detected"
    ROOT_CAUSE_REQUEST = "root_cause_request"
    REMEDIATION_REQUEST = "remediation_request"
    ANALYSIS_RESULT = "analysis_result"
    AGENT_STATUS = "agent_status"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: datetime
    service: str
    level: str
    message: str
    metadata: Dict[str, Any] = {}
    trace_id: Optional[str] = None

class Metric(BaseModel):
    """Metric data point"""
    timestamp: datetime
    service: str
    metric_name: str
    value: float
    labels: Dict[str, str] = {}

class Incident(BaseModel):
    """Incident model"""
    id: str = None
    title: str
    description: str
    severity: str  # critical, high, medium, low
    status: str = "open"  # open, investigating, resolved, closed
    created_at: datetime = None
    updated_at: datetime = None
    resolved_at: Optional[datetime] = None
    affected_services: List[str] = []
    root_cause: Optional[str] = None
    confidence_score: Optional[float] = None
    evidence: List[Dict[str, Any]] = []
    remediation_steps: List[str] = []
    timeline: List[Dict[str, Any]] = []
    assigned_to: Optional[str] = None
    tags: List[str] = []
    
    def __init__(self, **data):
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or not data['created_at']:
            data['created_at'] = datetime.utcnow()
        if 'updated_at' not in data or not data['updated_at']:
            data['updated_at'] = datetime.utcnow()
        super().__init__(**data)
    
    def add_timeline_entry(self, event: str, details: str = ""):
        """Add entry to incident timeline"""
        self.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "details": details
        })
        self.updated_at = datetime.utcnow()
    
    def add_evidence(self, evidence_type: str, data: Dict[str, Any]):
        """Add evidence to incident"""
        self.evidence.append({
            "type": evidence_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        })
    
    def update_status(self, status: str, reason: str = ""):
        """Update incident status"""
        old_status = self.status
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == "resolved":
            self.resolved_at = datetime.utcnow()
        
        self.add_timeline_entry(
            f"Status changed from {old_status} to {status}",
            reason
        )

class RootCauseHypothesis(BaseModel):
    """Root cause hypothesis model"""
    hypothesis: str
    confidence: float
    evidence: List[Dict[str, Any]]
    affected_components: List[str]
    reasoning_chain: List[str]
    validation_steps: List[str]

class RemediationPlan(BaseModel):
    """Remediation plan model"""
    incident_id: str
    title: str
    description: str
    risk_level: str  # low, medium, high
    estimated_duration: int  # minutes
    requires_approval: bool
    validation_steps: List[str]
    remediation_steps: List[Dict[str, Any]]
    rollback_plan: List[str]
    success_criteria: List[str]
    
class KnowledgeArticle(BaseModel):
    """Knowledge base article model"""
    id: str = None
    title: str
    content: str
    type: str  # runbook, troubleshooting, post_mortem
    tags: List[str] = []
    related_incidents: List[str] = []
    effectiveness_score: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    author: str = "system"
    
    def __init__(self, **data):
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or not data['created_at']:
            data['created_at'] = datetime.utcnow()
        if 'updated_at' not in data or not data['updated_at']:
            data['updated_at'] = datetime.utcnow()
        super().__init__(**data)

class AgentMessage(BaseModel):
    """Agent message model for communication between agents"""
    id: str = None
    sender_id: str
    recipient_id: str
    message_type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = None
    correlation_id: Optional[str] = None
    
    def __init__(self, **data):
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())
        if 'timestamp' not in data or not data['timestamp']:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)

class AgentStatus(BaseModel):
    """Agent status model"""
    agent_id: str
    name: str
    type: str
    status: str  # online, offline, error, starting, stopping
    last_heartbeat: datetime
    version: str
    capabilities: List[str]
    current_tasks: int
    total_processed: int
    error_count: int
    metadata: Dict[str, Any] = {}

class ServiceHealth(BaseModel):
    """Service health status"""
    service_name: str
    status: str  # healthy, degraded, unhealthy, unknown
    response_time_p95: float
    error_rate: float
    availability: float
    last_check: datetime
    metrics: Dict[str, float] = {}
    dependencies: List[str] = []
