"""
Analyzer Agent for NEXUS MVP
Performs root cause analysis and incident detection using Amazon Bedrock
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from .base_agent import BaseAgent
from ..models import Incident, LogEntry, AgentMessage, MessageType
from ..bedrock_client import get_bedrock_client
import config

logger = logging.getLogger(__name__)

class AnalyzerAgent(BaseAgent):
    """Agent responsible for analyzing logs and detecting incidents"""
    
    def __init__(self):
        super().__init__(
            agent_id="analyzer-001",
            agent_type="reasoning",
            capabilities=["incident_detection", "root_cause_analysis", "pattern_matching"]
        )
        self.incident_patterns = INCIDENT_PATTERNS
        self.service_topology = SERVICE_TOPOLOGY
        self.detection_config = INCIDENT_DETECTION
        self.active_incidents = {}
        self.analysis_history = []
        
        # Register message handlers
        self.register_handler("logs_processed", self._handle_logs_processed)
        self.register_handler("analyze_incident", self._handle_analyze_incident)
        self.register_handler("get_root_cause", self._handle_get_root_cause)
        self.register_handler("detect_anomalies", self._handle_detect_anomalies)
    
    async def initialize(self):
        """Initialize the analyzer"""
        print(f"Initializing Analyzer Agent...")
        print(f"Loaded {len(self.incident_patterns)} incident patterns")
        print(f"Monitoring {len(self.service_topology)} services")
    
    async def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up Analyzer Agent...")
    
    async def _handle_logs_processed(self, message: MCPMessage) -> MCPMessage:
        """Handle processed logs from ingester"""
        payload = message.payload
        logs = payload.get('logs', [])
        summary = payload.get('summary', {})
        
        print(f"Received {len(logs)} logs for analysis")
        
        # Detect incidents
        incidents = await self._detect_incidents(logs, summary)
        
        # Analyze each incident
        analysis_results = []
        for incident in incidents:
            analysis = await self._analyze_incident(incident, logs)
            analysis_results.append(analysis)
            
            # Send incident notification
            if analysis['severity'] in ['high', 'critical']:
                await self._notify_incident(analysis)
        
        return MCPMessage(
            message_type="analysis_completed",
            payload={
                'incidents_detected': len(incidents),
                'analysis_results': analysis_results,
                'timestamp': datetime.utcnow().isoformat()
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _detect_incidents(self, logs: List[Dict[str, Any]], summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect incidents from logs and summary"""
        incidents = []
        
        # Check error rate threshold
        error_rate = summary.get('error_rate', 0)
        if error_rate > self.detection_config['error_rate_threshold']:
            incidents.append({
                'type': 'high_error_rate',
                'description': f'High error rate detected: {error_rate:.2%}',
                'severity': 'high' if error_rate > 0.3 else 'medium',
                'affected_services': list(summary.get('service_distribution', {}).keys()),
                'evidence': {
                    'error_rate': error_rate,
                    'recent_errors': summary.get('recent_errors', [])
                }
            })
        
        # Check for anomalies
        anomalies = summary.get('anomalies_detected', [])
        for anomaly in anomalies:
            if anomaly.get('severity') in ['high', 'critical']:
                incidents.append({
                    'type': anomaly['type'],
                    'description': anomaly['description'],
                    'severity': anomaly['severity'],
                    'affected_services': [anomaly.get('affected_service')] if anomaly.get('affected_service') else [],
                    'evidence': {'anomaly_data': anomaly}
                })
        
        # Pattern-based detection
        pattern_incidents = await self._detect_pattern_incidents(logs)
        incidents.extend(pattern_incidents)
        
        return incidents
    
    async def _detect_pattern_incidents(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect incidents based on known patterns"""
        incidents = []
        
        for pattern_name, pattern in self.incident_patterns.items():
            # Check if pattern symptoms are present
            symptoms_detected = self._check_pattern_symptoms(logs, pattern)
            if symptoms_detected:
                incidents.append({
                    'type': 'pattern_match',
                    'pattern_name': pattern_name,
                    'description': pattern['description'],
                    'severity': 'high',
                    'affected_services': pattern['affected_services'],
                    'evidence': {
                        'pattern_match': pattern_name,
                        'symptoms_detected': symptoms_detected
                    }
                })
        
        return incidents
    
    def _check_pattern_symptoms(self, logs: List[Dict[str, Any]], pattern: Dict[str, Any]) -> List[str]:
        """Check if pattern symptoms are present in logs"""
        detected_symptoms = []
        symptoms = pattern.get('symptoms', [])
        
        for symptom in symptoms:
            if self._check_symptom_in_logs(logs, symptom):
                detected_symptoms.append(symptom)
        
        # Return symptoms if at least 50% are detected
        if len(detected_symptoms) >= len(symptoms) * 0.5:
            return detected_symptoms
        
        return []
    
    def _check_symptom_in_logs(self, logs: List[Dict[str, Any]], symptom: str) -> bool:
        """Check if a specific symptom is present in logs"""
        symptom_patterns = {
            'high_response_time': lambda log: 'response_time' in str(log.get('message', '')).lower() or 
                                           log.get('metadata', {}).get('response_time_ms', 0) > 2000,
            'connection_errors': lambda log: 'connection' in str(log.get('message', '')).lower() and 
                                           log.get('level') in ['ERROR', 'FATAL'],
            'timeout_errors': lambda log: 'timeout' in str(log.get('message', '')).lower() and 
                                        log.get('level') in ['ERROR', 'FATAL'],
            'increasing_memory_usage': lambda log: 'memory' in str(log.get('message', '')).lower() and 
                                                  'usage' in str(log.get('message', '')).lower(),
            'oom_errors': lambda log: 'out of memory' in str(log.get('message', '')).lower() or 
                                    'oom' in str(log.get('message', '')).lower(),
            'service_restarts': lambda log: 'restart' in str(log.get('message', '')).lower(),
            'api_errors': lambda log: log.get('metadata', {}).get('status_code', 200) >= 400,
            'failed_payments': lambda log: 'payment' in str(log.get('message', '')).lower() and 
                                         'failed' in str(log.get('message', '')).lower(),
            'database_load_increase': lambda log: 'database' in str(log.get('message', '')).lower() and 
                                                'load' in str(log.get('message', '')).lower(),
            'cache_misses': lambda log: 'cache miss' in str(log.get('message', '')).lower(),
            'queue_depth_increase': lambda log: 'queue' in str(log.get('message', '')).lower() and 
                                              'depth' in str(log.get('message', '')).lower(),
            'message_delays': lambda log: 'message' in str(log.get('message', '')).lower() and 
                                        'delay' in str(log.get('message', '')).lower(),
            'consumer_lag': lambda log: 'consumer' in str(log.get('message', '')).lower() and 
                                      'lag' in str(log.get('message', '')).lower()
        }
        
        pattern_check = symptom_patterns.get(symptom)
        if not pattern_check:
            return False
        
        # Check last 20 logs for symptom
        recent_logs = logs[-20:] if len(logs) > 20 else logs
        symptom_count = sum(1 for log in recent_logs if pattern_check(log))
        
        return symptom_count >= 2  # At least 2 occurrences
    
    async def _analyze_incident(self, incident: Dict[str, Any], logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed analysis of an incident"""
        analysis = {
            'incident_id': incident.get('incident_id', f"inc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
            'type': incident['type'],
            'description': incident['description'],
            'severity': incident['severity'],
            'affected_services': incident['affected_services'],
            'timestamp': datetime.utcnow().isoformat(),
            'root_cause_hypothesis': None,
            'confidence_score': 0.0,
            'evidence': [],
            'remediation_steps': [],
            'impact_assessment': {}
        }
        
        # Generate root cause hypothesis
        root_cause = await self._generate_root_cause_hypothesis(incident, logs)
        analysis['root_cause_hypothesis'] = root_cause['hypothesis']
        analysis['confidence_score'] = root_cause['confidence']
        analysis['evidence'] = root_cause['evidence']
        
        # Generate remediation steps
        remediation = await self._generate_remediation_steps(incident, root_cause)
        analysis['remediation_steps'] = remediation
        
        # Assess impact
        impact = self._assess_incident_impact(incident)
        analysis['impact_assessment'] = impact
        
        # Store analysis
        self.analysis_history.append(analysis)
        
        return analysis
    
    async def _generate_root_cause_hypothesis(self, incident: Dict[str, Any], logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate root cause hypothesis"""
        incident_type = incident['type']
        affected_services = incident['affected_services']
        
        # Pattern-based root cause analysis
        if incident_type == 'pattern_match':
            pattern_name = incident.get('pattern_name')
            if pattern_name in self.incident_patterns:
                pattern = self.incident_patterns[pattern_name]
                return {
                    'hypothesis': pattern['root_cause'],
                    'confidence': 0.85,
                    'evidence': [
                        {
                            'type': 'pattern_match',
                            'description': f'Matches known pattern: {pattern_name}',
                            'data': pattern
                        }
                    ],
                    'reasoning_chain': [
                        f"Detected symptoms: {pattern.get('symptoms', [])}",
                        f"Pattern matches: {pattern_name}",
                        f"Known root cause: {pattern['root_cause']}"
                    ]
                }
        
        # Error rate analysis
        elif incident_type == 'high_error_rate':
            error_evidence = incident.get('evidence', {})
            recent_errors = error_evidence.get('recent_errors', [])
            
            # Analyze error patterns
            error_services = {}
            error_types = {}
            for error in recent_errors:
                service = error.get('service', 'unknown')
                message = error.get('message', '')
                error_services[service] = error_services.get(service, 0) + 1
                error_types[message] = error_types.get(message, 0) + 1
            
            # Find most frequent error
            most_frequent_error = max(error_types.items(), key=lambda x: x[1]) if error_types else None
            most_affected_service = max(error_services.items(), key=lambda x: x[1]) if error_services else None
            
            hypothesis = f"High error rate likely caused by issues in {most_affected_service[0] if most_affected_service else 'multiple services'}"
            if most_frequent_error:
                hypothesis += f" - most frequent error: {most_frequent_error[0][:50]}..."
            
            return {
                'hypothesis': hypothesis,
                'confidence': 0.7,
                'evidence': [
                    {
                        'type': 'error_analysis',
                        'description': 'Error pattern analysis',
                        'data': {
                            'error_services': error_services,
                            'error_types': dict(list(error_types.items())[:5])  # Top 5 errors
                        }
                    }
                ],
                'reasoning_chain': [
                    f"Error rate: {error_evidence.get('error_rate', 0):.2%}",
                    f"Most affected service: {most_affected_service[0] if most_affected_service else 'unknown'}",
                    f"Primary error pattern identified"
                ]
            }
        
        # Service-specific analysis
        elif incident_type == 'service_degradation':
            affected_service = affected_services[0] if affected_services else 'unknown'
            service_info = self.service_topology.get(affected_service, {})
            dependencies = service_info.get('dependencies', [])
            
            hypothesis = f"Service {affected_service} degradation likely due to dependency issues"
            if dependencies:
                hypothesis += f" - check dependencies: {', '.join(dependencies[:3])}"
            
            return {
                'hypothesis': hypothesis,
                'confidence': 0.75,
                'evidence': [
                    {
                        'type': 'service_topology',
                        'description': 'Service dependency analysis',
                        'data': service_info
                    }
                ],
                'reasoning_chain': [
                    f"Service {affected_service} showing degradation",
                    f"Dependencies to check: {dependencies}",
                    f"Service type: {service_info.get('type', 'unknown')}"
                ]
            }
        
        # Default analysis
        return {
            'hypothesis': f"Unknown incident type: {incident_type} - requires manual investigation",
            'confidence': 0.3,
            'evidence': [
                {
                    'type': 'basic_analysis',
                    'description': 'Limited automated analysis available',
                    'data': incident
                }
            ],
            'reasoning_chain': [
                f"Incident type: {incident_type}",
                f"Affected services: {affected_services}",
                "Requires manual investigation"
            ]
        }
    
    async def _generate_remediation_steps(self, incident: Dict[str, Any], root_cause: Dict[str, Any]) -> List[str]:
        """Generate remediation steps"""
        incident_type = incident['type']
        
        # Pattern-based remediation
        if incident_type == 'pattern_match':
            pattern_name = incident.get('pattern_name')
            if pattern_name in self.incident_patterns:
                return self.incident_patterns[pattern_name]['remediation']
        
        # Generic remediation steps
        generic_steps = [
            "1. Verify incident scope and affected services",
            "2. Check service health and dependencies",
            "3. Review recent deployments or changes",
            "4. Analyze error logs and metrics",
            "5. Implement temporary mitigation if needed",
            "6. Apply root cause fix",
            "7. Monitor for resolution",
            "8. Document incident and lessons learned"
        ]
        
        return generic_steps
    
    def _assess_incident_impact(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the impact of an incident"""
        affected_services = incident['affected_services']
        severity = incident['severity']
        
        # Calculate criticality based on service topology
        total_criticality = 0
        high_criticality_services = 0
        
        for service in affected_services:
            service_info = self.service_topology.get(service, {})
            criticality = service_info.get('criticality', 'low')
            if criticality == 'high':
                total_criticality += 3
                high_criticality_services += 1
            elif criticality == 'medium':
                total_criticality += 2
            else:
                total_criticality += 1
        
        # Estimate affected users (simplified)
        user_impact = "low"
        if high_criticality_services > 0:
            user_impact = "high"
        elif total_criticality > 5:
            user_impact = "medium"
        
        return {
            'user_impact': user_impact,
            'business_impact': severity,
            'affected_service_count': len(affected_services),
            'high_criticality_services': high_criticality_services,
            'estimated_affected_users': self._estimate_affected_users(affected_services),
            'downstream_services': self._get_downstream_services(affected_services)
        }
    
    def _estimate_affected_users(self, services: List[str]) -> str:
        """Estimate number of affected users"""
        if any(service in ['auth-service', 'payment-service'] for service in services):
            return "10,000+"
        elif any(service in ['user-service'] for service in services):
            return "5,000+"
        else:
            return "< 1,000"
    
    def _get_downstream_services(self, services: List[str]) -> List[str]:
        """Get services that depend on the affected services"""
        downstream = set()
        for service in services:
            for svc_name, svc_info in self.service_topology.items():
                if service in svc_info.get('dependencies', []):
                    downstream.add(svc_name)
        return list(downstream)
    
    async def _notify_incident(self, analysis: Dict[str, Any]):
        """Send incident notification"""
        notification = MCPMessage(
            message_type="incident_detected",
            payload={
                'incident': analysis,
                'priority': 'high' if analysis['severity'] in ['high', 'critical'] else 'medium',
                'requires_immediate_attention': analysis['severity'] == 'critical'
            },
            source=self.agent_id,
            target="remediation-001"
        )
        await self.send_message(notification)
    
    async def _handle_analyze_incident(self, message: MCPMessage) -> MCPMessage:
        """Handle incident analysis request"""
        payload = message.payload
        incident_data = payload.get('incident')
        logs = payload.get('logs', [])
        
        analysis = await self._analyze_incident(incident_data, logs)
        
        return MCPMessage(
            message_type="incident_analysis_response",
            payload={'analysis': analysis},
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_get_root_cause(self, message: MCPMessage) -> MCPMessage:
        """Handle root cause analysis request"""
        payload = message.payload
        incident_id = payload.get('incident_id')
        
        # Find analysis in history
        analysis = None
        for hist in self.analysis_history:
            if hist.get('incident_id') == incident_id:
                analysis = hist
                break
        
        return MCPMessage(
            message_type="root_cause_response",
            payload={
                'incident_id': incident_id,
                'analysis': analysis,
                'found': analysis is not None
            },
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
    
    async def _handle_detect_anomalies(self, message: MCPMessage) -> MCPMessage:
        """Handle anomaly detection request"""
        payload = message.payload
        metrics = payload.get('metrics', [])
        
        # Simple anomaly detection (placeholder)
        anomalies = []
        
        return MCPMessage(
            message_type="anomalies_detected",
            payload={'anomalies': anomalies},
            source=self.agent_id,
            target=message.source,
            correlation_id=message.correlation_id
        )
