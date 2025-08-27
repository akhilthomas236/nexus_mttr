"""
Analyzer Agent for NEXUS MVP
Performs root cause analysis and incident detection using Amazon Bedrock
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .base_agent import BaseAgent
from models import Incident, LogEntry, AgentMessage, MessageType
from bedrock_client import get_bedrock_client
import config

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    """
    Agent responsible for analyzing logs and detecting incidents using AI
    Integrates with Amazon Bedrock for advanced analysis capabilities
    """
    
    def __init__(self, agent_id: str = "analyzer-agent"):
        super().__init__(
            agent_id=agent_id, 
            agent_type="analysis", 
            capabilities=["log_analysis", "incident_detection", "root_cause_analysis"]
        )
        self.bedrock_client = get_bedrock_client()
        self.active_incidents: Dict[str, Incident] = {}
        self.analysis_history: List[Dict] = []
        
        # Detection thresholds from config
        self.error_rate_threshold = 0.15
        self.response_time_threshold = 5000
        self.availability_threshold = 0.95
        self.detection_window_minutes = 5
        
        logger.info(f"Analyzer Agent initialized with Bedrock: {self.bedrock_client.is_available()}")
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages for analysis requests"""
        try:
            if message.message_type == MessageType.LOG_ANALYSIS:
                # Analyze logs for incidents
                log_data = message.data
                incidents = await self.analyze_logs_for_incidents(log_data)
                
                if incidents:
                    # Send incident detected message
                    response = AgentMessage(
                        sender_id=self.agent_id,
                        recipient_id="broadcast",
                        message_type=MessageType.INCIDENT_DETECTED,
                        data={
                            'incidents': [incident.model_dump() for incident in incidents],
                            'analysis_timestamp': datetime.utcnow().isoformat()
                        },
                        timestamp=datetime.utcnow()
                    )
                    return response
                    
            elif message.message_type == MessageType.ROOT_CAUSE_REQUEST:
                # Perform root cause analysis
                incident_data = message.data.get('incident')
                if incident_data:
                    root_cause = await self.perform_root_cause_analysis(incident_data)
                    
                    response = AgentMessage(
                        sender_id=self.agent_id,
                        recipient_id=message.sender_id,
                        message_type=MessageType.ANALYSIS_RESULT,
                        data={
                            'root_cause_analysis': root_cause,
                            'incident_id': incident_data.get('id')
                        },
                        timestamp=datetime.utcnow()
                    )
                    return response
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    async def analyze_logs_for_incidents(self, log_data: Dict) -> List[Incident]:
        """Analyze log data for potential incidents using Bedrock AI"""
        logger.info("Analyzing logs for incidents using Bedrock AI")
        
        try:
            log_entries = log_data.get('log_entries', [])
            anomalies = log_data.get('anomalies', [])
            
            if not log_entries:
                return []
            
            # Use Bedrock to analyze logs
            log_text = [f"{entry.get('timestamp', '')} {entry.get('level', '')} {entry.get('service', '')} {entry.get('message', '')}" 
                       for entry in log_entries[:50]]  # Limit for API efficiency
            
            analysis_result = await self.bedrock_client.analyze_logs(
                log_text, 
                context=f"Analyzing {len(log_entries)} log entries with {len(anomalies)} detected anomalies"
            )
            
            incidents = []
            
            # Process Bedrock analysis results
            bedrock_incidents = analysis_result.get('incidents', [])
            
            for bedrock_incident in bedrock_incidents:
                incident = self._create_incident_from_analysis(bedrock_incident, log_entries, anomalies)
                if incident:
                    incidents.append(incident)
                    self.active_incidents[incident.id] = incident
            
            # Also check for pattern-based incidents (fallback)
            pattern_incidents = await self.detect_incidents_by_patterns(log_entries, anomalies)
            incidents.extend(pattern_incidents)
            
            logger.info(f"Detected {len(incidents)} incidents from log analysis")
            return incidents
            
        except Exception as e:
            logger.error(f"Error in log analysis: {e}")
            # Fallback to pattern-based detection
            return await self.detect_incidents_by_patterns(log_data.get('log_entries', []), log_data.get('anomalies', []))
    
    def _create_incident_from_analysis(self, bedrock_incident: Dict, log_entries: List, anomalies: List) -> Optional[Incident]:
        """Create an Incident object from Bedrock analysis"""
        try:
            incident_id = f"inc-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(self.active_incidents)}"
            
            incident = Incident(
                id=incident_id,
                title=bedrock_incident.get('title', 'AI Detected Incident'),
                description=bedrock_incident.get('description', 'Incident detected by AI analysis'),
                severity=bedrock_incident.get('severity', 'medium'),
                status='open',
                affected_services=bedrock_incident.get('affected_services', ['unknown']),
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                confidence_score=bedrock_incident.get('confidence', 0.7)
            )
            
            return incident
            
        except Exception as e:
            logger.error(f"Error creating incident from analysis: {e}")
            return None
    
    async def detect_incidents_by_patterns(self, log_entries: List, anomalies: List) -> List[Incident]:
        """Fallback pattern-based incident detection"""
        incidents = []
        
        # Group logs by service
        service_logs = {}
        for entry in log_entries:
            service = entry.get('service', 'unknown')
            if service not in service_logs:
                service_logs[service] = []
            service_logs[service].append(entry)
        
        # Check each service for incident patterns
        for service, logs in service_logs.items():
            incident = await self._check_service_for_incidents(service, logs, anomalies)
            if incident:
                incidents.append(incident)
                self.active_incidents[incident.id] = incident
        
        return incidents
    
    async def _check_service_for_incidents(self, service: str, logs: List, anomalies: List) -> Optional[Incident]:
        """Check a specific service for incident patterns"""
        try:
            # Count errors in the logs
            error_count = sum(1 for log in logs if log.get('level') in ['ERROR', 'FATAL'])
            total_logs = len(logs)
            
            if total_logs == 0:
                return None
            
            error_rate = error_count / total_logs
            
            # Check if error rate exceeds threshold
            if error_rate > self.error_rate_threshold:
                incident_id = f"inc-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{service}"
                
                incident = Incident(
                    id=incident_id,
                    title=f"High Error Rate in {service}",
                    description=f"Error rate of {error_rate:.1%} detected in {service} (threshold: {self.error_rate_threshold:.1%})",
                    severity=self._determine_severity(error_rate),
                    status='open',
                    affected_services=[service],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    confidence_score=min(0.9, error_rate * 2)  # Higher error rate = higher confidence
                )
                
                return incident
                
        except Exception as e:
            logger.error(f"Error checking service {service} for incidents: {e}")
        
        return None
    
    def _determine_severity(self, error_rate: float) -> str:
        """Determine incident severity based on error rate"""
        if error_rate >= 0.5:
            return 'critical'
        elif error_rate >= 0.3:
            return 'high'
        elif error_rate >= 0.15:
            return 'medium'
        else:
            return 'low'
    
    async def perform_root_cause_analysis(self, incident_data: Dict) -> Dict:
        """Perform root cause analysis using Bedrock AI"""
        logger.info(f"Performing root cause analysis for incident: {incident_data.get('id')}")
        
        try:
            # Prepare evidence for analysis
            evidence = []
            evidence.append(f"Incident: {incident_data.get('title', 'Unknown')}")
            evidence.append(f"Description: {incident_data.get('description', 'No description')}")
            evidence.append(f"Affected Services: {', '.join(incident_data.get('affected_services', []))}")
            evidence.append(f"Severity: {incident_data.get('severity', 'unknown')}")
            evidence.append(f"First Seen: {incident_data.get('first_seen', 'unknown')}")
            
            # Use Bedrock for root cause analysis
            analysis = await self.bedrock_client.perform_root_cause_analysis(
                incident_description=incident_data.get('description', ''),
                evidence=evidence
            )
            
            # Store analysis in history
            self.analysis_history.append({
                'incident_id': incident_data.get('id'),
                'analysis': analysis,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"Root cause analysis completed with confidence: {analysis.get('confidence', 0)}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in root cause analysis: {e}")
            # Return fallback analysis
            return {
                'root_causes': [
                    {'cause': 'Service degradation detected', 'confidence': 0.5}
                ],
                'analysis_steps': [
                    'Basic pattern analysis performed',
                    'Service metrics reviewed'
                ],
                'contributing_factors': ['Unknown factors'],
                'confidence': 0.4
            }
    
    async def detect_incidents(self, anomalies: List[Dict]) -> List[Incident]:
        """Detect incidents from anomaly data"""
        incidents = []
        
        # Group anomalies by service
        service_anomalies = {}
        for anomaly in anomalies:
            service = anomaly.get('service', 'unknown')
            if service not in service_anomalies:
                service_anomalies[service] = []
            service_anomalies[service].append(anomaly)
        
        # Create incidents for services with significant anomalies
        for service, service_anomaly_list in service_anomalies.items():
            high_severity_anomalies = [a for a in service_anomaly_list if a.get('severity') in ['high', 'critical']]
            
            if len(high_severity_anomalies) >= 2:  # Multiple high-severity anomalies
                incident_id = f"inc-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{service}"
                
                incident = Incident(
                    id=incident_id,
                    title=f"Multiple Anomalies Detected in {service}",
                    description=f"Detected {len(high_severity_anomalies)} high-severity anomalies in {service}",
                    severity='high' if len(high_severity_anomalies) >= 3 else 'medium',
                    status='open',
                    affected_services=[service],
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    confidence_score=min(0.9, len(high_severity_anomalies) * 0.3)
                )
                
                incidents.append(incident)
                self.active_incidents[incident.id] = incident
        
        return incidents
    
    async def analyze_root_cause(self, incident: Incident, evidence: List[Dict]) -> Dict:
        """Analyze root cause for an incident"""
        try:
            # Convert evidence to text format
            evidence_text = []
            for item in evidence:
                if isinstance(item, dict):
                    evidence_text.append(f"{item.get('type', 'Evidence')}: {item.get('description', str(item))}")
                else:
                    evidence_text.append(str(item))
            
            # Use Bedrock for analysis
            analysis = await self.bedrock_client.perform_root_cause_analysis(
                incident_description=incident.description,
                evidence=evidence_text
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in root cause analysis: {e}")
            return {
                'root_causes': [{'cause': 'Analysis error occurred', 'confidence': 0.1}],
                'analysis_steps': ['Error in analysis pipeline'],
                'contributing_factors': ['System error'],
                'confidence': 0.1
            }
    
    async def get_incident_status(self, incident_id: str) -> Optional[Dict]:
        """Get status of a specific incident"""
        incident = self.active_incidents.get(incident_id)
        if incident:
            return incident.model_dump()
        return None
    
    async def run(self):
        """Main run loop for the Analyzer Agent"""
        logger.info(f"Analyzer Agent {self.agent_id} starting...")
        
        # Test Bedrock connection
        if self.bedrock_client.is_available():
            logger.info("Bedrock AI integration active")
        else:
            logger.warning("Bedrock AI not available - using pattern-based analysis")
        
        while self.running:
            try:
                # Process any pending messages
                await self.process_pending_messages()
                
                # Clean up old incidents (older than 24 hours)
                await self._cleanup_old_incidents()
                
                # Send heartbeat
                await self.send_heartbeat()
                
                # Wait before next iteration
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in analyzer agent run loop: {e}")
                await asyncio.sleep(15)
        
        logger.info(f"Analyzer Agent {self.agent_id} stopped")
    
    async def _cleanup_old_incidents(self):
        """Clean up old resolved incidents"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            incidents_to_remove = []
            for incident_id, incident in self.active_incidents.items():
                if incident.status == 'resolved' and incident.resolved_at and incident.resolved_at < cutoff_time:
                    incidents_to_remove.append(incident_id)
            
            for incident_id in incidents_to_remove:
                del self.active_incidents[incident_id]
                logger.debug(f"Cleaned up old incident: {incident_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old incidents: {e}")
    
    async def initialize(self):
        """Initialize the analyzer agent"""
        logger.info(f"Analyzer Agent {self.agent_id} initialized")
        # Add any initialization logic here
        pass
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info(f"Analyzer Agent {self.agent_id} cleaning up")
        # Add any cleanup logic here
        pass


async def main():
    """Test the Analyzer Agent"""
    agent = AnalyzerAgent()
    
    # Test log analysis
    test_log_data = {
        'log_entries': [
            {
                'timestamp': '2024-01-15 10:00:00',
                'level': 'ERROR',
                'service': 'auth-service',
                'message': 'Database connection failed'
            },
            {
                'timestamp': '2024-01-15 10:01:00', 
                'level': 'ERROR',
                'service': 'auth-service',
                'message': 'Authentication timeout'
            },
            {
                'timestamp': '2024-01-15 10:02:00',
                'level': 'FATAL',
                'service': 'auth-service', 
                'message': 'Service unavailable'
            }
        ],
        'anomalies': [
            {
                'service': 'auth-service',
                'metric': 'error_rate',
                'severity': 'high',
                'value': 0.8
            }
        ]
    }
    
    incidents = await agent.analyze_logs_for_incidents(test_log_data)
    print(f"Detected {len(incidents)} incidents")
    
    if incidents:
        incident = incidents[0]
        print(f"Incident: {incident.title}")
        print(f"Severity: {incident.severity}")
        
        # Test root cause analysis
        root_cause = await agent.analyze_root_cause(incident, [])
        print(f"Root cause analysis: {root_cause}")


if __name__ == "__main__":
    asyncio.run(main())
