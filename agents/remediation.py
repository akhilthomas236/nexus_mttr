"""
Remediation Agent for NEXUS MVP
Generates automated remediation plans, runbooks, and recovery scripts
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from .base_agent import BaseAgent
from models import Incident, AgentMessage, MessageType
from bedrock_client import get_bedrock_client

logger = logging.getLogger(__name__)


class RemediationAgent(BaseAgent):
    """
    Agent responsible for generating automated remediation plans,
    runbooks, and recovery scripts for detected incidents.
    """
    
    def __init__(self, agent_id: str = "remediation-agent"):
        super().__init__(
            agent_id=agent_id,
            agent_type="remediation", 
            capabilities=["remediation_planning", "runbook_generation", "automation_scripts"]
        )
        self.bedrock_client = get_bedrock_client()
        self.remediation_templates = self._load_remediation_templates()
        self.runbook_library = self._initialize_runbook_library()
        
        logger.info(f"Remediation Agent initialized with Bedrock: {self.bedrock_client.is_available()}")
        
    def _load_remediation_templates(self) -> Dict:
        """Load predefined remediation templates for common incident types"""
        return {
            "high_cpu": {
                "priority": "high",
                "steps": [
                    "Identify processes consuming high CPU",
                    "Check for runaway processes or memory leaks",
                    "Scale horizontally if needed",
                    "Restart affected services if safe",
                    "Monitor recovery progress"
                ],
                "scripts": {
                    "diagnosis": "top -n 1 | head -20; ps aux --sort=-%cpu | head -10",
                    "mitigation": "systemctl restart {service_name}",
                    "scaling": "kubectl scale deployment {deployment} --replicas={replicas}"
                }
            },
            "memory_exhaustion": {
                "priority": "critical",
                "steps": [
                    "Identify memory-consuming processes",
                    "Check for memory leaks",
                    "Free up memory by restarting services",
                    "Scale up memory allocation",
                    "Implement memory monitoring"
                ],
                "scripts": {
                    "diagnosis": "free -h; ps aux --sort=-%mem | head -10",
                    "mitigation": "systemctl restart {service_name}",
                    "cleanup": "echo 3 > /proc/sys/vm/drop_caches"
                }
            },
            "disk_space": {
                "priority": "high",
                "steps": [
                    "Identify large files and directories",
                    "Clean up temporary files",
                    "Archive old logs",
                    "Expand disk space if needed",
                    "Set up log rotation"
                ],
                "scripts": {
                    "diagnosis": "df -h; du -sh /* | sort -hr | head -10",
                    "cleanup": "find /tmp -type f -atime +7 -delete",
                    "log_cleanup": "journalctl --vacuum-time=7d"
                }
            },
            "service_down": {
                "priority": "critical",
                "steps": [
                    "Check service status",
                    "Review recent logs for errors",
                    "Attempt service restart",
                    "Verify dependencies are running",
                    "Escalate if restart fails"
                ],
                "scripts": {
                    "diagnosis": "systemctl status {service_name}; journalctl -u {service_name} --since '10 minutes ago'",
                    "mitigation": "systemctl restart {service_name}",
                    "verification": "systemctl is-active {service_name}"
                }
            },
            "network_latency": {
                "priority": "medium",
                "steps": [
                    "Check network connectivity",
                    "Test latency to key endpoints",
                    "Review network configuration",
                    "Check for network congestion",
                    "Contact network team if needed"
                ],
                "scripts": {
                    "diagnosis": "ping -c 5 {endpoint}; traceroute {endpoint}",
                    "bandwidth_test": "iperf3 -c {server} -t 10",
                    "dns_check": "nslookup {domain}"
                }
            },
            "database_connection": {
                "priority": "critical",
                "steps": [
                    "Check database service status",
                    "Verify connection pool settings",
                    "Test database connectivity",
                    "Review database logs",
                    "Restart connection pools if needed"
                ],
                "scripts": {
                    "diagnosis": "systemctl status postgresql; netstat -an | grep 5432",
                    "connection_test": "psql -h {host} -U {user} -c 'SELECT 1;'",
                    "pool_restart": "systemctl restart pgbouncer"
                }
            }
        }
    
    def _initialize_runbook_library(self) -> Dict:
        """Initialize library of operational runbooks"""
        return {
            "incident_response_checklist": [
                "Acknowledge incident and start timer",
                "Assemble incident response team",
                "Establish communication channels",
                "Begin initial assessment",
                "Implement immediate mitigation",
                "Document all actions taken",
                "Communicate status to stakeholders",
                "Conduct post-incident review"
            ],
            "service_restart_procedure": [
                "Check service dependencies",
                "Drain traffic if load balanced",
                "Stop service gracefully",
                "Wait for complete shutdown",
                "Start service",
                "Verify service health",
                "Restore traffic routing",
                "Monitor for stability"
            ],
            "database_recovery": [
                "Assess database state",
                "Check for corruption",
                "Stop application connections",
                "Create backup if possible",
                "Restore from last known good backup",
                "Replay transaction logs",
                "Verify data integrity",
                "Restore application connections"
            ]
        }
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming messages for remediation requests"""
        try:
            if message.message_type == MessageType.INCIDENT_DETECTED:
                # Generate remediation plan for new incident
                incident_data = message.data.get('incident')
                if incident_data:
                    incident = Incident(**incident_data)
                    remediation_plan = await self.generate_remediation_plan(incident)
                    
                    response = AgentMessage(
                        sender_id=self.agent_id,
                        recipient_id=message.sender_id,
                        message_type=MessageType.ANALYSIS_RESULT,
                        data={
                            'remediation_plan': remediation_plan,
                            'incident_id': incident.id
                        },
                        timestamp=datetime.utcnow()
                    )
                    return response
                    
            elif message.message_type == MessageType.REMEDIATION_REQUEST:
                # Handle specific remediation requests
                incident_id = message.data.get('incident_id')
                request_type = message.data.get('request_type', 'full_plan')
                
                if request_type == 'runbook':
                    runbook = await self.generate_runbook(message.data)
                    response_data = {'runbook': runbook}
                elif request_type == 'scripts':
                    scripts = await self.generate_automation_scripts(message.data)
                    response_data = {'scripts': scripts}
                else:
                    # Generate full remediation plan
                    plan = await self.generate_remediation_plan_from_data(message.data)
                    response_data = {'remediation_plan': plan}
                
                response = AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.ANALYSIS_RESULT,
                    data=response_data,
                    timestamp=datetime.utcnow()
                )
                return response
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return None
    
    async def generate_remediation_plan(self, incident: Incident) -> Dict:
        """Generate comprehensive remediation plan for an incident using Bedrock AI"""
        logger.info(f"Generating remediation plan for incident {incident.id}")
        
        try:
            # Try Bedrock AI-powered remediation plan generation
            if self.bedrock_client.is_available():
                ai_plan = await self.bedrock_client.generate_remediation_plan(
                    incident_type=self._classify_incident_type(incident),
                    root_cause=incident.description,
                    affected_services=incident.affected_services
                )
                
                # Enhance AI plan with template-based details
                enhanced_plan = await self._enhance_ai_plan_with_templates(incident, ai_plan)
                return enhanced_plan
                
        except Exception as e:
            logger.warning(f"Bedrock AI remediation failed, falling back to templates: {e}")
        
        # Fallback to template-based approach
        return await self._generate_template_based_plan(incident)
    
    async def _enhance_ai_plan_with_templates(self, incident: Incident, ai_plan: Dict) -> Dict:
        """Enhance AI-generated plan with template-based automation scripts"""
        incident_type = self._classify_incident_type(incident)
        template = self.remediation_templates.get(incident_type, {})
        
        # Merge AI plan with template data
        enhanced_plan = {
            'incident_id': incident.id,
            'incident_type': incident_type,
            'priority': ai_plan.get('priority', template.get('priority', 'medium')),
            'estimated_resolution_time': self._estimate_resolution_time(incident, incident_type),
            'immediate_actions': ai_plan.get('immediate_actions', template.get('steps', [])[:2]),
            'detailed_steps': self._format_ai_steps(ai_plan.get('detailed_steps', [])),
            'automation_scripts': self._generate_automation_scripts_for_incident(incident, template),
            'rollback_plan': ai_plan.get('rollback_plan', self._generate_rollback_plan(incident)),
            'verification_steps': ai_plan.get('verification_steps', self._generate_verification_steps(incident)),
            'monitoring_recommendations': ai_plan.get('prevention_measures', self._generate_monitoring_recommendations(incident)),
            'ai_generated': True,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Enhanced AI plan with {len(enhanced_plan['detailed_steps'])} steps")
        return enhanced_plan
    
    def _format_ai_steps(self, ai_steps: List) -> List[Dict]:
        """Format AI-generated steps into detailed step format"""
        formatted_steps = []
        
        for i, step in enumerate(ai_steps, 1):
            if isinstance(step, str):
                formatted_step = {
                    'step_number': i,
                    'description': step,
                    'estimated_time': '5-10 minutes',
                    'commands': [],
                    'verification': 'Manual verification required',
                    'rollback': 'Document changes for potential rollback'
                }
            elif isinstance(step, dict):
                formatted_step = {
                    'step_number': i,
                    'description': step.get('action', step.get('description', f'Step {i}')),
                    'estimated_time': step.get('time_estimate', '5-10 minutes'),
                    'commands': step.get('commands', []),
                    'verification': step.get('verification', 'Manual verification required'),
                    'rollback': step.get('rollback', 'Document changes for potential rollback')
                }
            else:
                formatted_step = {
                    'step_number': i,
                    'description': str(step),
                    'estimated_time': '5-10 minutes',
                    'commands': [],
                    'verification': 'Manual verification required',
                    'rollback': 'Document changes for potential rollback'
                }
            
            formatted_steps.append(formatted_step)
        
        return formatted_steps
    
    async def _generate_template_based_plan(self, incident: Incident) -> Dict:
        """Generate remediation plan using templates (fallback method)"""
        # Analyze incident type and severity
        incident_type = self._classify_incident_type(incident)
        
        # Get base template
        template = self.remediation_templates.get(incident_type, {})
        
        # Generate customized plan
        plan = {
            'incident_id': incident.id,
            'incident_type': incident_type,
            'priority': template.get('priority', 'medium'),
            'estimated_resolution_time': self._estimate_resolution_time(incident, incident_type),
            'immediate_actions': self._generate_immediate_actions(incident, template),
            'detailed_steps': self._generate_detailed_steps(incident, template),
            'automation_scripts': self._generate_automation_scripts_for_incident(incident, template),
            'rollback_plan': self._generate_rollback_plan(incident),
            'verification_steps': self._generate_verification_steps(incident),
            'monitoring_recommendations': self._generate_monitoring_recommendations(incident),
            'ai_generated': False,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Generated {len(plan['detailed_steps'])} step template-based remediation plan")
        return plan
    
    def _classify_incident_type(self, incident: Incident) -> str:
        """Classify incident type based on description and context"""
        description = incident.description.lower()
        
        # Simple keyword-based classification
        if any(keyword in description for keyword in ['cpu', 'processor', 'load']):
            return 'high_cpu'
        elif any(keyword in description for keyword in ['memory', 'ram', 'oom']):
            return 'memory_exhaustion'
        elif any(keyword in description for keyword in ['disk', 'storage', 'space']):
            return 'disk_space'
        elif any(keyword in description for keyword in ['service', 'down', 'unavailable']):
            return 'service_down'
        elif any(keyword in description for keyword in ['network', 'latency', 'timeout']):
            return 'network_latency'
        elif any(keyword in description for keyword in ['database', 'connection', 'sql']):
            return 'database_connection'
        else:
            return 'general'
    
    def _estimate_resolution_time(self, incident: Incident, incident_type: str) -> str:
        """Estimate resolution time based on incident severity and type"""
        time_estimates = {
            'critical': {
                'service_down': '15-30 minutes',
                'memory_exhaustion': '10-20 minutes',
                'database_connection': '20-45 minutes',
                'default': '30-60 minutes'
            },
            'high': {
                'high_cpu': '20-40 minutes',
                'disk_space': '15-30 minutes',
                'default': '45-90 minutes'
            },
            'medium': {
                'network_latency': '30-60 minutes',
                'default': '1-2 hours'
            },
            'low': {
                'default': '2-4 hours'
            }
        }
        
        severity_estimates = time_estimates.get(incident.severity, time_estimates['medium'])
        return severity_estimates.get(incident_type, severity_estimates['default'])
    
    def _generate_immediate_actions(self, incident: Incident, template: Dict) -> List[str]:
        """Generate immediate actions to take"""
        actions = []
        
        if incident.severity == 'critical':
            actions.append("Page on-call team immediately")
            actions.append("Start incident war room/bridge")
        
        actions.append("Acknowledge incident in monitoring system")
        actions.append("Begin impact assessment")
        
        # Add template-specific immediate actions
        template_steps = template.get('steps', [])
        if template_steps:
            actions.extend(template_steps[:2])  # First 2 steps as immediate
        
        return actions
    
    def _generate_detailed_steps(self, incident: Incident, template: Dict) -> List[Dict]:
        """Generate detailed remediation steps"""
        steps = []
        template_steps = template.get('steps', [])
        
        for i, step in enumerate(template_steps, 1):
            step_detail = {
                'step_number': i,
                'description': step,
                'estimated_time': '5-10 minutes',
                'commands': self._get_commands_for_step(step, template),
                'verification': self._get_verification_for_step(step),
                'rollback': self._get_rollback_for_step(step)
            }
            steps.append(step_detail)
        
        return steps
    
    def _get_commands_for_step(self, step: str, template: Dict) -> List[str]:
        """Get shell commands for a remediation step"""
        scripts = template.get('scripts', {})
        commands = []
        
        step_lower = step.lower()
        
        if 'identify' in step_lower or 'check' in step_lower:
            commands.extend(scripts.get('diagnosis', '').split('; '))
        elif 'restart' in step_lower:
            commands.append(scripts.get('mitigation', ''))
        elif 'scale' in step_lower:
            commands.append(scripts.get('scaling', ''))
        elif 'clean' in step_lower:
            commands.append(scripts.get('cleanup', ''))
        
        return [cmd.strip() for cmd in commands if cmd.strip()]
    
    def _get_verification_for_step(self, step: str) -> str:
        """Get verification command for a step"""
        step_lower = step.lower()
        
        if 'restart' in step_lower:
            return "systemctl is-active {service_name}"
        elif 'scale' in step_lower:
            return "kubectl get pods | grep {deployment}"
        elif 'clean' in step_lower:
            return "df -h"
        else:
            return "echo 'Manual verification required'"
    
    def _get_rollback_for_step(self, step: str) -> str:
        """Get rollback procedure for a step"""
        step_lower = step.lower()
        
        if 'restart' in step_lower:
            return "Restart can be reversed by stopping service"
        elif 'scale' in step_lower:
            return "Scale back to original replica count"
        elif 'clean' in step_lower:
            return "Restore from backup if files were critical"
        else:
            return "Document changes for potential rollback"
    
    def _generate_automation_scripts_for_incident(self, incident: Incident, template: Dict) -> Dict:
        """Generate automation scripts for the incident"""
        scripts = template.get('scripts', {})
        
        # Customize scripts with incident-specific parameters
        customized_scripts = {}
        
        for script_type, script_template in scripts.items():
            # Extract service name from incident if possible
            service_name = self._extract_service_name(incident)
            
            customized_script = script_template.format(
                service_name=service_name,
                deployment=service_name,
                replicas=3,  # Default scaling
                endpoint=incident.affected_services[0] if incident.affected_services else 'localhost',
                host=incident.affected_services[0] if incident.affected_services else 'localhost',
                user='app_user',
                domain=incident.affected_services[0] if incident.affected_services else 'localhost',
                server='localhost'
            )
            
            customized_scripts[script_type] = customized_script
        
        return customized_scripts
    
    def _extract_service_name(self, incident: Incident) -> str:
        """Extract service name from incident information"""
        if incident.affected_services:
            return incident.affected_services[0]
        
        # Try to extract from description
        description_words = incident.description.lower().split()
        common_services = ['nginx', 'apache', 'mysql', 'postgresql', 'redis', 'docker']
        
        for word in description_words:
            if word in common_services:
                return word
        
        return 'unknown-service'
    
    def _generate_rollback_plan(self, incident: Incident) -> Dict:
        """Generate rollback plan"""
        return {
            'triggers': [
                'Resolution attempts fail after 3 tries',
                'System state worsens',
                'New critical issues arise'
            ],
            'steps': [
                'Stop current remediation actions',
                'Restore previous configuration',
                'Verify system stability',
                'Escalate to senior team'
            ],
            'time_limit': '30 minutes',
            'escalation_contacts': [
                'senior-ops-team@company.com',
                'infrastructure-lead@company.com'
            ]
        }
    
    def _generate_verification_steps(self, incident: Incident) -> List[str]:
        """Generate verification steps to confirm resolution"""
        return [
            'Check service health endpoints',
            'Verify metrics have returned to normal',
            'Test affected functionality manually',
            'Confirm no new alerts are firing',
            'Monitor for 15 minutes to ensure stability'
        ]
    
    def _generate_monitoring_recommendations(self, incident: Incident) -> List[str]:
        """Generate recommendations for improved monitoring"""
        return [
            'Add alerting for early detection of similar issues',
            'Implement health checks for affected services',
            'Set up automated recovery for common scenarios',
            'Create dashboard for key metrics',
            'Schedule regular system health reviews'
        ]
    
    async def generate_remediation_plan_from_data(self, data: Dict) -> Dict:
        """Generate remediation plan from message data"""
        # This is a simplified version for handling direct requests
        incident_type = data.get('incident_type', 'general')
        severity = data.get('severity', 'medium')
        
        template = self.remediation_templates.get(incident_type, {})
        
        plan = {
            'incident_type': incident_type,
            'priority': template.get('priority', 'medium'),
            'steps': template.get('steps', ['Manual investigation required']),
            'scripts': template.get('scripts', {}),
            'estimated_time': '30-60 minutes',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return plan
    
    async def generate_runbook(self, data: Dict) -> Dict:
        """Generate operational runbook"""
        runbook_type = data.get('runbook_type', 'incident_response_checklist')
        
        runbook = {
            'type': runbook_type,
            'steps': self.runbook_library.get(runbook_type, []),
            'estimated_time': '45 minutes',
            'prerequisites': [
                'Access to monitoring systems',
                'Administrative privileges',
                'Incident response training'
            ],
            'tools_required': [
                'SSH access',
                'Monitoring dashboard',
                'Communication platform'
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return runbook
    
    async def generate_automation_scripts(self, data: Dict) -> Dict:
        """Generate automation scripts for specific scenarios"""
        incident_type = data.get('incident_type', 'general')
        template = self.remediation_templates.get(incident_type, {})
        
        scripts = {
            'diagnosis_script': self._create_diagnosis_script(template),
            'mitigation_script': self._create_mitigation_script(template),
            'verification_script': self._create_verification_script(template),
            'rollback_script': self._create_rollback_script(template)
        }
        
        return scripts
    
    def _create_diagnosis_script(self, template: Dict) -> str:
        """Create diagnostic script"""
        diagnosis_commands = template.get('scripts', {}).get('diagnosis', 'echo "No diagnosis script available"')
        
        script = f"""#!/bin/bash
# Diagnostic script generated by NEXUS Remediation Agent
# Generated at: {datetime.utcnow().isoformat()}

echo "Starting diagnostic checks..."
{diagnosis_commands}
echo "Diagnostic checks complete."
"""
        return script
    
    def _create_mitigation_script(self, template: Dict) -> str:
        """Create mitigation script"""
        mitigation_commands = template.get('scripts', {}).get('mitigation', 'echo "No mitigation script available"')
        
        script = f"""#!/bin/bash
# Mitigation script generated by NEXUS Remediation Agent
# Generated at: {datetime.utcnow().isoformat()}

echo "Starting mitigation actions..."
{mitigation_commands}
echo "Mitigation actions complete."
"""
        return script
    
    def _create_verification_script(self, template: Dict) -> str:
        """Create verification script"""
        verification_commands = template.get('scripts', {}).get('verification', 'echo "Manual verification required"')
        
        script = f"""#!/bin/bash
# Verification script generated by NEXUS Remediation Agent
# Generated at: {datetime.utcnow().isoformat()}

echo "Starting verification checks..."
{verification_commands}
echo "Verification complete."
"""
        return script
    
    def _create_rollback_script(self, template: Dict) -> str:
        """Create rollback script"""
        script = f"""#!/bin/bash
# Rollback script generated by NEXUS Remediation Agent
# Generated at: {datetime.utcnow().isoformat()}

echo "Starting rollback procedures..."
echo "WARNING: This will undo recent changes"
read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Executing rollback..."
    # Add specific rollback commands here
    echo "Rollback complete."
else
    echo "Rollback cancelled."
fi
"""
        return script
    
    async def run(self):
        """Main run loop for the Remediation Agent"""
        logger.info(f"Remediation Agent {self.agent_id} starting...")
        
        while self.running:
            try:
                # Process any pending messages
                await self.process_pending_messages()
                
                # Send heartbeat
                await self.send_heartbeat()
                
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in remediation agent run loop: {e}")
                await asyncio.sleep(10)
        
        logger.info(f"Remediation Agent {self.agent_id} stopped")
    
    async def initialize(self):
        """Initialize the remediation agent"""
        logger.info(f"Remediation Agent {self.agent_id} initialized")
        # Add any initialization logic here
        pass
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info(f"Remediation Agent {self.agent_id} cleaning up")
        # Add any cleanup logic here
        pass


async def main():
    """Test the Remediation Agent"""
    agent = RemediationAgent()
    
    # Test incident for remediation planning
    test_incident = Incident(
        id="test-incident-001",
        title="High CPU Usage Alert",
        description="CPU usage has exceeded 90% on web-server-01 for the past 10 minutes",
        severity="high",
        status="open",
        affected_services=["web-server-01"],
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )
    
    # Generate remediation plan
    plan = await agent.generate_remediation_plan(test_incident)
    print("Generated Remediation Plan:")
    print(json.dumps(plan, indent=2, default=str))
    
    # Test runbook generation
    runbook = await agent.generate_runbook({'runbook_type': 'service_restart_procedure'})
    print("\nGenerated Runbook:")
    print(json.dumps(runbook, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
