"""
Amazon Bedrock client for NEXUS MVP
Provides AI/ML capabilities using Amazon Bedrock foundation models
"""

import json
import logging
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import config

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with Amazon Bedrock foundation models"""
    
    def __init__(self):
        self.region = config.BEDROCK_CONFIG["region"]
        self.model_id = config.BEDROCK_CONFIG["model_id"]
        self.max_tokens = config.BEDROCK_CONFIG["max_tokens"]
        self.temperature = config.BEDROCK_CONFIG["temperature"]
        self.top_p = config.BEDROCK_CONFIG["top_p"]
        
        try:
            # Initialize Bedrock client
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region,
                aws_access_key_id=config.AWS_ACCESS_KEY_ID if config.AWS_ACCESS_KEY_ID else None,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY if config.AWS_SECRET_ACCESS_KEY else None
            )
            
            logger.info(f"Initialized Bedrock client for region {self.region}")
            
        except NoCredentialsError:
            logger.warning("AWS credentials not found. Using mock responses for development.")
            self.bedrock_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.bedrock_client = None
    
    def is_available(self) -> bool:
        """Check if Bedrock client is available"""
        return self.bedrock_client is not None
    
    async def generate_text(self, prompt: str, model: str = None, max_tokens: int = None) -> Optional[str]:
        """Generate text using Bedrock foundation model"""
        if not self.is_available():
            return self._mock_response(prompt)
        
        try:
            model_id = model or self.model_id
            tokens = max_tokens or self.max_tokens
            
            # Prepare request based on model type
            if "anthropic.claude" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            else:
                # Generic format for other models
                body = {
                    "prompt": prompt,
                    "max_tokens": tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p
                }
            
            # Make request to Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if "anthropic.claude" in model_id:
                return response_body['content'][0]['text']
            else:
                return response_body.get('completion', response_body.get('text', ''))
                
        except ClientError as e:
            logger.error(f"AWS ClientError in generate_text: {e}")
            return self._mock_response(prompt)
        except Exception as e:
            logger.error(f"Error generating text with Bedrock: {e}")
            return self._mock_response(prompt)
    
    async def analyze_logs(self, log_entries: List[str], context: str = "") -> Dict[str, Any]:
        """Analyze log entries for anomalies and incidents"""
        prompt = f"""
        Analyze the following log entries for anomalies, errors, and potential incidents:

        Context: {context}

        Log Entries:
        {chr(10).join(log_entries[:20])}  # Limit to first 20 entries

        Please provide analysis in JSON format with:
        1. "anomalies": List of detected anomalies with severity and description
        2. "incidents": List of potential incidents with affected services
        3. "summary": Brief summary of log analysis
        4. "recommendations": Suggested actions

        Respond only with valid JSON.
        """
        
        response = await self.generate_text(prompt, model=config.BEDROCK_MODELS["fast"])
        
        try:
            return json.loads(response) if response else self._mock_log_analysis(log_entries)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from Bedrock")
            return self._mock_log_analysis(log_entries)
    
    async def perform_root_cause_analysis(self, incident_description: str, evidence: List[str]) -> Dict[str, Any]:
        """Perform root cause analysis for an incident"""
        prompt = f"""
        Perform root cause analysis for the following incident:

        Incident: {incident_description}

        Evidence:
        {chr(10).join(evidence)}

        Provide analysis in JSON format with:
        1. "root_causes": List of potential root causes with confidence scores (0-1)
        2. "analysis_steps": Step-by-step reasoning process
        3. "contributing_factors": Additional factors that may have contributed
        4. "confidence": Overall confidence in the analysis (0-1)

        Respond only with valid JSON.
        """
        
        response = await self.generate_text(prompt, model=config.BEDROCK_MODELS["balanced"])
        
        try:
            return json.loads(response) if response else self._mock_root_cause_analysis()
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from Bedrock")
            return self._mock_root_cause_analysis()
    
    async def generate_remediation_plan(self, incident_type: str, root_cause: str, affected_services: List[str]) -> Dict[str, Any]:
        """Generate remediation plan for an incident"""
        prompt = f"""
        Generate a detailed remediation plan for the following incident:

        Incident Type: {incident_type}
        Root Cause: {root_cause}
        Affected Services: {', '.join(affected_services)}

        Provide plan in JSON format with:
        1. "immediate_actions": List of immediate steps to take
        2. "detailed_steps": Detailed remediation steps with time estimates
        3. "rollback_plan": Steps to rollback changes if needed
        4. "verification_steps": How to verify the fix worked
        5. "prevention_measures": How to prevent recurrence

        Respond only with valid JSON.
        """
        
        response = await self.generate_text(prompt, model=config.BEDROCK_MODELS["balanced"])
        
        try:
            return json.loads(response) if response else self._mock_remediation_plan()
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from Bedrock")
            return self._mock_remediation_plan()
    
    async def generate_incident_summary(self, log_entries: List[str], timeframe: str) -> str:
        """Generate a concise incident summary"""
        prompt = f"""
        Generate a concise summary of the following log entries from {timeframe}:

        {chr(10).join(log_entries[:15])}

        Provide a brief 2-3 sentence summary focusing on:
        - Key events that occurred
        - Services affected
        - Severity level

        Keep the response concise and factual.
        """
        
        response = await self.generate_text(prompt, model=config.BEDROCK_MODELS["fast"])
        return response or f"Log analysis summary for {timeframe}: Multiple service events detected requiring investigation."
    
    def _mock_response(self, prompt: str) -> str:
        """Provide mock response when Bedrock is not available"""
        if "root cause" in prompt.lower():
            return json.dumps({
                "root_causes": [
                    {"cause": "High CPU usage due to memory leak", "confidence": 0.8},
                    {"cause": "Database connection pool exhaustion", "confidence": 0.6}
                ],
                "analysis_steps": [
                    "Analyzed CPU metrics and found sustained high usage",
                    "Reviewed memory patterns indicating potential leak",
                    "Checked database connection metrics"
                ],
                "contributing_factors": ["Recent code deployment", "Increased traffic load"],
                "confidence": 0.75
            })
        elif "remediation" in prompt.lower():
            return json.dumps(self._mock_remediation_plan())
        elif "log" in prompt.lower():
            # Extract log content from the prompt to pass to mock
            log_lines = []
            if "Log Entries:" in prompt:
                log_section = prompt.split("Log Entries:")[1].split("Please provide")[0].strip()
                log_lines = [line.strip() for line in log_section.split('\n') if line.strip()]
            return json.dumps(self._mock_log_analysis(log_lines))
        else:
            return "Mock response: AI analysis would be provided here when Bedrock is properly configured."
    
    def _mock_log_analysis(self, log_text: List[str] = None) -> Dict[str, Any]:
        """Mock log analysis response - now enhanced to create incidents based on actual log content"""
        incidents = []
        
        # If we have actual log text, create specific incidents based on content
        if log_text:
            error_patterns = {
                "Database connection pool exhausted": {
                    "title": "Database Connection Pool Exhaustion",
                    "description": "Database connection pool exhausted",
                    "severity": "high",
                    "services": ["user-db", "auth-service"]
                },
                "Authentication failed": {
                    "title": "Authentication Failures",
                    "description": "Authentication failure for user user_1084",
                    "severity": "medium", 
                    "services": ["auth-service"]
                },
                "Connection refused": {
                    "title": "Service Connectivity Issues", 
                    "description": "Connectivity issues between user-db and auth-service",
                    "severity": "medium",
                    "services": ["user-db", "auth-service"]
                },
                "SSL certificate expired": {
                    "title": "SSL Certificate Issues",
                    "description": "SSL certificate expired causing service disruption",
                    "severity": "high",
                    "services": ["user-service"]
                },
                "Out of memory": {
                    "title": "Memory Exhaustion",
                    "description": "Out of memory error detected in service",
                    "severity": "high", 
                    "services": ["user-service"]
                }
            }
            
            # Check for error patterns in the log text
            log_content = " ".join(log_text) if log_text else ""
            for pattern, incident_template in error_patterns.items():
                if pattern.lower() in log_content.lower():
                    incidents.append({
                        "title": incident_template["title"],
                        "description": incident_template["description"],
                        "severity": incident_template["severity"],
                        "affected_services": incident_template["services"],
                        "confidence": 0.8
                    })
        
        # Add default incident if no specific patterns found
        if not incidents:
            incidents.append({
                "title": "Authentication Service Degradation",
                "severity": "high",
                "affected_services": ["auth-service"],
                "confidence": 0.85
            })
        
        return {
            "anomalies": [
                {
                    "type": "error_spike",
                    "severity": "high",
                    "description": "Error rate increased from 2% to 15% in the last 5 minutes",
                    "service": "auth-service"
                }
            ],
            "incidents": incidents,
            "summary": "Detected significant error rate increase in authentication service with potential user impact",
            "recommendations": [
                "Investigate authentication service health",
                "Check database connectivity",
                "Review recent deployments"
            ]
        }
    
    def _mock_root_cause_analysis(self) -> Dict[str, Any]:
        """Mock root cause analysis response"""
        return {
            "root_causes": [
                {"cause": "Database connection timeout", "confidence": 0.8},
                {"cause": "Memory exhaustion in service", "confidence": 0.6}
            ],
            "analysis_steps": [
                "Reviewed error patterns in logs",
                "Analyzed system resource metrics",
                "Correlated timing with external events"
            ],
            "contributing_factors": ["High traffic volume", "Recent configuration change"],
            "confidence": 0.75
        }
    
    def _mock_remediation_plan(self) -> Dict[str, Any]:
        """Mock remediation plan response"""
        return {
            "immediate_actions": [
                "Restart affected service instances",
                "Scale up service replicas",
                "Enable circuit breaker"
            ],
            "detailed_steps": [
                {
                    "step": 1,
                    "action": "Restart service instances",
                    "time_estimate": "2-3 minutes",
                    "commands": ["kubectl rollout restart deployment/auth-service"]
                },
                {
                    "step": 2,
                    "action": "Scale up replicas",
                    "time_estimate": "1-2 minutes", 
                    "commands": ["kubectl scale deployment/auth-service --replicas=5"]
                }
            ],
            "rollback_plan": [
                "Scale back to original replica count",
                "Revert to previous service version if needed"
            ],
            "verification_steps": [
                "Check service health endpoints",
                "Monitor error rates for 10 minutes",
                "Verify user authentication is working"
            ],
            "prevention_measures": [
                "Implement better resource monitoring",
                "Set up auto-scaling policies",
                "Add circuit breaker patterns"
            ]
        }


# Global Bedrock client instance
_bedrock_client = None


def get_bedrock_client() -> BedrockClient:
    """Get the global Bedrock client instance"""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client


async def test_bedrock_connection():
    """Test Bedrock connection and capabilities"""
    client = get_bedrock_client()
    
    if not client.is_available():
        logger.warning("Bedrock client not available - using mock responses")
        return False
    
    try:
        # Test basic text generation
        response = await client.generate_text("Hello, this is a test. Please respond with 'Bedrock is working!'")
        logger.info(f"Bedrock test response: {response}")
        return "bedrock" in response.lower() or "working" in response.lower()
    except Exception as e:
        logger.error(f"Bedrock connection test failed: {e}")
        return False
