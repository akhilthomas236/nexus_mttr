#!/usr/bin/env python3
"""
Test script for NEXUS MVP agents
Validates agent functionality and integration
"""

import asyncio
import json
import logging
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.log_ingester import LogIngesterAgent
from agents.analyzer import AnalyzerAgent
from agents.remediation import RemediationAgent
from models import LogEntry, Incident, AgentMessage, MessageType
import config

logger = logging.getLogger(__name__)


class NexusTestSuite:
    """Test suite for NEXUS MVP components"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🧪 Starting NEXUS MVP Test Suite")
        logger.info("="*50)
        
        # Test individual agents
        await self.test_log_ingester()
        await self.test_analyzer_agent()
        await self.test_remediation_agent()
        
        # Test integration scenarios
        await self.test_end_to_end_scenario()
        await self.test_message_passing()
        
        # Print results
        self.print_test_results()
    
    async def test_log_ingester(self):
        """Test Log Ingester Agent"""
        logger.info("Testing Log Ingester Agent...")
        
        try:
            agent = LogIngesterAgent()
            
            # Test 1: Create sample log file
            test_logs = self.create_test_log_file()
            
            # Test 2: Process log file
            result = await agent.process_log_file(test_logs)
            
            # Validate results
            assert result is not None, "Log processing returned None"
            assert 'log_entries' in result, "Missing log_entries in result"
            assert 'anomalies' in result, "Missing anomalies in result"
            assert len(result['log_entries']) > 0, "No log entries processed"
            
            self.record_test("Log Ingester - Basic Processing", True, "Successfully processed log file")
            
            # Test 3: Anomaly detection
            anomalies = result.get('anomalies', [])
            has_cpu_anomaly = any('CPU' in str(anomaly) for anomaly in anomalies)
            
            self.record_test("Log Ingester - Anomaly Detection", has_cpu_anomaly, 
                           f"Found {len(anomalies)} anomalies, CPU anomaly: {has_cpu_anomaly}")
            
            # Test 4: Message generation
            message = await agent.generate_log_summary(result['log_entries'][:10])
            assert message is not None, "Failed to generate log summary"
            
            self.record_test("Log Ingester - Summary Generation", True, "Generated log summary")
            
        except Exception as e:
            self.record_test("Log Ingester Tests", False, f"Error: {e}")
            logger.error(f"Log Ingester test failed: {e}")
    
    async def test_analyzer_agent(self):
        """Test Analyzer Agent"""
        logger.info("Testing Analyzer Agent...")
        
        try:
            agent = AnalyzerAgent()
            
            # Test 1: Incident detection from sample data
            sample_anomalies = [
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'web-server-01',
                    'metric': 'cpu_usage',
                    'value': 95.5,
                    'threshold': 80.0,
                    'severity': 'high'
                }
            ]
            
            incidents = await agent.detect_incidents(sample_anomalies)
            assert len(incidents) > 0, "No incidents detected from high CPU anomaly"
            
            incident = incidents[0]
            assert incident.severity in ['low', 'medium', 'high', 'critical'], "Invalid incident severity"
            assert 'web-server-01' in incident.affected_services, "Service not correctly identified"
            
            self.record_test("Analyzer - Incident Detection", True, 
                           f"Detected {len(incidents)} incidents")
            
            # Test 2: Root cause analysis
            root_cause = await agent.analyze_root_cause(incident, sample_anomalies)
            assert root_cause is not None, "Root cause analysis failed"
            assert len(root_cause) > 0, "Empty root cause analysis"
            
            self.record_test("Analyzer - Root Cause Analysis", True, 
                           f"Generated root cause analysis: {len(root_cause)} factors")
            
            # Test 3: Message processing
            test_message = AgentMessage(
                sender_id="test-sender",
                recipient_id=agent.agent_id,
                message_type=MessageType.LOG_ANALYSIS,
                data={'anomalies': sample_anomalies},
                timestamp=datetime.utcnow()
            )
            
            response = await agent.process_message(test_message)
            assert response is not None, "No response to message"
            assert response.message_type == MessageType.INCIDENT_DETECTED, "Wrong response type"
            
            self.record_test("Analyzer - Message Processing", True, "Processed message correctly")
            
        except Exception as e:
            self.record_test("Analyzer Tests", False, f"Error: {e}")
            logger.error(f"Analyzer test failed: {e}")
    
    async def test_remediation_agent(self):
        """Test Remediation Agent"""
        logger.info("Testing Remediation Agent...")
        
        try:
            agent = RemediationAgent()
            
            # Test 1: Create test incident
            test_incident = Incident(
                id="test-incident-001",
                title="High CPU Usage Test",
                description="CPU usage exceeded 90% on web-server-01",
                severity="high",
                status="open",
                affected_services=["web-server-01"],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            
            # Test 2: Generate remediation plan
            plan = await agent.generate_remediation_plan(test_incident)
            
            assert plan is not None, "Remediation plan generation failed"
            assert 'incident_id' in plan, "Missing incident_id in plan"
            assert 'immediate_actions' in plan, "Missing immediate_actions in plan"
            assert 'detailed_steps' in plan, "Missing detailed_steps in plan"
            assert len(plan['detailed_steps']) > 0, "No detailed steps in plan"
            
            self.record_test("Remediation - Plan Generation", True, 
                           f"Generated plan with {len(plan['detailed_steps'])} steps")
            
            # Test 3: Runbook generation
            runbook = await agent.generate_runbook({'runbook_type': 'service_restart_procedure'})
            
            assert runbook is not None, "Runbook generation failed"
            assert 'steps' in runbook, "Missing steps in runbook"
            assert len(runbook['steps']) > 0, "No steps in runbook"
            
            self.record_test("Remediation - Runbook Generation", True, 
                           f"Generated runbook with {len(runbook['steps'])} steps")
            
            # Test 4: Script generation
            scripts = await agent.generate_automation_scripts({'incident_type': 'high_cpu'})
            
            assert scripts is not None, "Script generation failed"
            assert 'diagnosis_script' in scripts, "Missing diagnosis script"
            assert 'mitigation_script' in scripts, "Missing mitigation script"
            
            self.record_test("Remediation - Script Generation", True, 
                           f"Generated {len(scripts)} scripts")
            
        except Exception as e:
            self.record_test("Remediation Tests", False, f"Error: {e}")
            logger.error(f"Remediation test failed: {e}")
    
    async def test_end_to_end_scenario(self):
        """Test complete end-to-end scenario"""
        logger.info("Testing End-to-End Scenario...")
        
        try:
            # Initialize all agents
            log_ingester = LogIngesterAgent()
            analyzer = AnalyzerAgent()
            remediation = RemediationAgent()
            
            # Step 1: Create test log file with incident data
            test_logs = self.create_incident_log_file()
            
            # Step 2: Process logs
            log_result = await log_ingester.process_log_file(test_logs)
            assert log_result is not None, "Log processing failed"
            
            # Step 3: Analyze for incidents
            anomalies = log_result.get('anomalies', [])
            incidents = await analyzer.detect_incidents(anomalies)
            assert len(incidents) > 0, "No incidents detected in e2e test"
            
            # Step 4: Generate remediation plan
            incident = incidents[0]
            plan = await remediation.generate_remediation_plan(incident)
            assert plan is not None, "Remediation plan generation failed in e2e test"
            
            self.record_test("End-to-End Scenario", True, 
                           f"Successfully processed logs → detected {len(incidents)} incidents → generated remediation plan")
            
        except Exception as e:
            self.record_test("End-to-End Scenario", False, f"Error: {e}")
            logger.error(f"End-to-end test failed: {e}")
    
    async def test_message_passing(self):
        """Test inter-agent message passing"""
        logger.info("Testing Message Passing...")
        
        try:
            analyzer = AnalyzerAgent()
            remediation = RemediationAgent()
            
            # Test message from analyzer to remediation
            test_incident_data = {
                'id': 'test-msg-001',
                'title': 'Test Message Incident',
                'description': 'Test incident for message passing',
                'severity': 'medium',
                'status': 'open',
                'affected_services': ['test-service'],
                'first_seen': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()
            }
            
            message = AgentMessage(
                sender_id=analyzer.agent_id,
                recipient_id=remediation.agent_id,
                message_type=MessageType.INCIDENT_DETECTED,
                data={'incident': test_incident_data},
                timestamp=datetime.utcnow()
            )
            
            # Process message
            response = await remediation.process_message(message)
            
            assert response is not None, "No response from remediation agent"
            assert response.message_type == MessageType.ANALYSIS_RESULT, "Wrong response message type"
            assert 'remediation_plan' in response.data, "Missing remediation_plan in response"
            
            self.record_test("Message Passing", True, "Successfully passed message between agents")
            
        except Exception as e:
            self.record_test("Message Passing", False, f"Error: {e}")
            logger.error(f"Message passing test failed: {e}")
    
    def create_test_log_file(self) -> str:
        """Create a test log file with sample data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            # Normal logs
            f.write("2024-01-15 10:00:00 INFO web-server-01 Application started successfully\n")
            f.write("2024-01-15 10:01:00 INFO web-server-01 Processing request GET /api/users\n")
            f.write("2024-01-15 10:02:00 INFO web-server-01 Request completed in 150ms\n")
            
            # High CPU logs
            f.write("2024-01-15 10:05:00 WARN web-server-01 CPU usage: 85%\n")
            f.write("2024-01-15 10:06:00 ERROR web-server-01 CPU usage: 92%\n")
            f.write("2024-01-15 10:07:00 CRITICAL web-server-01 CPU usage: 98%\n")
            
            # More normal logs
            f.write("2024-01-15 10:10:00 INFO web-server-01 Processing request GET /api/health\n")
            f.write("2024-01-15 10:11:00 INFO web-server-01 Health check passed\n")
            
            return f.name
    
    def create_incident_log_file(self) -> str:
        """Create a log file that should trigger incident detection"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            base_time = datetime.utcnow()
            
            for i in range(30):
                timestamp = (base_time + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S')
                
                if 10 <= i <= 20:  # Incident period
                    f.write(f"{timestamp} ERROR web-server-01 CPU usage exceeded 95%\n")
                    f.write(f"{timestamp} ERROR web-server-01 Memory usage: 89%\n")
                    f.write(f"{timestamp} WARN web-server-01 Response time: 5.2s\n")
                else:  # Normal operation
                    f.write(f"{timestamp} INFO web-server-01 Processing request\n")
                    f.write(f"{timestamp} INFO web-server-01 Response time: 120ms\n")
            
            return f.name
    
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
        
        self.test_results.append({
            'name': test_name,
            'status': status,
            'details': details
        })
        
        logger.info(f"{status} {test_name}: {details}")
    
    def print_test_results(self):
        """Print final test results"""
        logger.info("\n" + "="*60)
        logger.info("🧪 NEXUS MVP TEST RESULTS")
        logger.info("="*60)
        
        for result in self.test_results:
            logger.info(f"{result['status']} {result['name']}")
            if result['details']:
                logger.info(f"    {result['details']}")
        
        logger.info("-"*60)
        logger.info(f"Tests Passed: {self.tests_passed}")
        logger.info(f"Tests Failed: {self.tests_failed}")
        logger.info(f"Total Tests: {self.tests_passed + self.tests_failed}")
        
        if self.tests_failed == 0:
            logger.info("🎉 All tests passed!")
        else:
            logger.info(f"⚠️  {self.tests_failed} test(s) failed")
        
        logger.info("="*60)


async def run_performance_test():
    """Run performance tests"""
    logger.info("🚀 Running Performance Tests...")
    
    # Test log processing speed
    log_ingester = LogIngesterAgent()
    
    # Create large test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        for i in range(10000):  # 10k log entries
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{timestamp} INFO test-service-{i%10} Test log entry {i}\n")
        
        large_file = f.name
    
    # Time the processing
    start_time = datetime.utcnow()
    result = await log_ingester.process_log_file(large_file)
    end_time = datetime.utcnow()
    
    processing_time = (end_time - start_time).total_seconds()
    entries_per_second = len(result['log_entries']) / processing_time if processing_time > 0 else 0
    
    logger.info(f"📊 Performance Results:")
    logger.info(f"   Processed {len(result['log_entries'])} entries in {processing_time:.2f}s")
    logger.info(f"   Rate: {entries_per_second:.1f} entries/second")
    
    # Clean up
    Path(large_file).unlink()


async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run NEXUS MVP tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    test_suite = NexusTestSuite()
    await test_suite.run_all_tests()
    
    if args.performance:
        await run_performance_test()
    
    # Exit with error code if tests failed
    if test_suite.tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
